"""DRC-5R — Read-only audit: FOTOPRINCIPAL, PROMOCAO_GESTAO, CADEIA, OBSESPECIFIC.

Never prints credentials or raw binary. Writes metadata JSON only.
"""
from __future__ import annotations

import hashlib
import json
import re
import struct
import sys
from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pyodbc

ENV = Path(__file__).resolve().parents[1] / ".env"
OUT = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "dynamic-retail-content"
    / "reconciliation"
    / "module-5r-ciss-offers-images.json"
)


def load_conn_parts() -> dict[str, str]:
    text = ENV.read_text(encoding="utf-8")
    m = re.search(r'DB2_CONN_STRING="([^"]+)"', text)
    if not m:
        raise SystemExit("DB2_CONN_STRING not found")
    raw = m.group(1)
    return {k: v for k, v in (p.split("=", 1) for p in raw.split(";") if "=" in p)}


def connect():
    parts = load_conn_parts()
    driver = "IBM DB2 ODBC DRIVER"
    conn_str = (
        f"Driver={{{driver}}};"
        f"Database={parts.get('DATABASE')};"
        f"Hostname={parts.get('HOSTNAME')};"
        f"Port={parts.get('PORT')};"
        f"Protocol={parts.get('PROTOCOL', 'TCPIP')};"
        f"Uid={parts.get('UID')};"
        f"Pwd={parts.get('PWD')};"
    )
    return pyodbc.connect(conn_str, timeout=45), parts.get("SCHEMA", "DBA")


def detect_magic(blob: bytes | None) -> dict[str, Any]:
    if not blob:
        return {"mime": None, "format": "EMPTY", "width": None, "height": None}
    b = bytes(blob[:64])
    fmt = "UNKNOWN"
    mime = None
    w = h = None
    if b[:3] == b"\xff\xd8\xff":
        fmt, mime = "JPEG", "image/jpeg"
        # soft SOF scan
        i = 2
        data = bytes(blob)
        while i < min(len(data) - 9, 200000):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in {0xC0, 0xC1, 0xC2}:
                h = struct.unpack(">H", data[i + 5 : i + 7])[0]
                w = struct.unpack(">H", data[i + 7 : i + 9])[0]
                break
            if marker in {0xD8, 0xD9}:
                i += 2
                continue
            if i + 4 > len(data):
                break
            seg_len = struct.unpack(">H", data[i + 2 : i + 4])[0]
            i += 2 + seg_len
    elif b[:8] == b"\x89PNG\r\n\x1a\n":
        fmt, mime = "PNG", "image/png"
        if len(blob) >= 24:
            w, h = struct.unpack(">II", bytes(blob[16:24]))
    elif b[:2] == b"BM":
        fmt, mime = "BMP", "image/bmp"
    elif b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        fmt, mime = "WEBP", "image/webp"
    elif b[:5] == b"<?xml" or b[:1] == b"<":
        fmt, mime = "XML/TEXT", "text/xml"
    elif all(32 <= c < 127 or c in (9, 10, 13) for c in b[:32]):
        fmt, mime = "TEXTISH", "text/plain"
    return {
        "mime": mime,
        "format": fmt,
        "width": w,
        "height": h,
        "sha256_12": hashlib.sha256(bytes(blob)).hexdigest()[:12] if blob else None,
        "byte_len": len(blob) if blob else 0,
        "head_hex": bytes(blob[:8]).hex() if blob else None,
    }


def cols(cur, schema: str, table: str) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT COLNAME, TYPENAME, LENGTH, SCALE, NULLS, REMARKS
        FROM SYSCAT.COLUMNS
        WHERE TABSCHEMA = ? AND TABNAME = ?
        ORDER BY COLNO
        """,
        schema,
        table,
    )
    return [
        {
            "name": r[0].strip() if isinstance(r[0], str) else r[0],
            "type": r[1].strip() if isinstance(r[1], str) else r[1],
            "length": int(r[2]) if r[2] is not None else None,
            "scale": int(r[3]) if r[3] is not None else None,
            "nullable": r[4],
        }
        for r in cur.fetchall()
    ]


def table_exists(cur, schema: str, table: str) -> bool:
    cur.execute(
        "SELECT 1 FROM SYSCAT.TABLES WHERE TABSCHEMA=? AND TABNAME=? FETCH FIRST 1 ROW ONLY",
        schema,
        table,
    )
    return cur.fetchone() is not None


def main() -> int:
    report: dict[str, Any] = {
        "module": "5R",
        "audited_at": datetime.utcnow().isoformat() + "Z",
        "read_only": True,
    }
    cn, schema = connect()
    cur = cn.cursor()
    print("CONNECTED schema=", schema)

    # --- columns metadata ---
    targets = [
        "PRODUTO_ESPECIFICACAO_TECNICA",
        "PROMOCAO_GESTAO",
        "PROMOCAO_GESTAO_PRODUTO",
        "PRODUTO_CADEIA_PRECO",
        "PRODUTO_GRADE",
        "PRODUTOS_VIEW",
    ]
    report["tables"] = {}
    for t in targets:
        exists = table_exists(cur, schema, t)
        report["tables"][t] = {"exists": exists, "columns": cols(cur, schema, t) if exists else []}
        print(f"TABLE {t} exists={exists} cols={len(report['tables'][t]['columns'])}")

    # --- FOTOPRINCIPAL sample ---
    image_meta: list[dict[str, Any]] = []
    length_dist: Counter[int] = Counter()
    format_dist: Counter[str] = Counter()
    if report["tables"]["PRODUTO_ESPECIFICACAO_TECNICA"]["exists"]:
        cur.execute(
            f"""
            SELECT IDCODBARPROD,
                   LENGTH(FOTOPRINCIPAL) AS L,
                   FOTOPRINCIPAL,
                   OBSESPECIFIC
            FROM {schema}.PRODUTO_ESPECIFICACAO_TECNICA
            WHERE FOTOPRINCIPAL IS NOT NULL
            ORDER BY LENGTH(FOTOPRINCIPAL) DESC
            FETCH FIRST 40 ROWS ONLY
            """
        )
        rows = cur.fetchall()
        for r in rows:
            blob = r[2]
            raw = bytes(blob) if blob is not None else b""
            length_dist[len(raw)] += 1
            info = detect_magic(raw)
            format_dist[info["format"]] += 1
            image_meta.append(
                {
                    "idcodbarprod": str(r[0]),
                    "length": len(raw),
                    "format": info["format"],
                    "mime": info["mime"],
                    "width": info["width"],
                    "height": info["height"],
                    "sha256_12": info["sha256_12"],
                    "head_hex": info["head_hex"],
                    "obsespecific_preview": (str(r[3] or "")[:80] or None),
                }
            )
        # length=4912 specifically
        cur.execute(
            f"""
            SELECT COUNT(*),
                   MIN(LENGTH(FOTOPRINCIPAL)),
                   MAX(LENGTH(FOTOPRINCIPAL)),
                   AVG(DECIMAL(LENGTH(FOTOPRINCIPAL), 15, 2))
            FROM {schema}.PRODUTO_ESPECIFICACAO_TECNICA
            WHERE FOTOPRINCIPAL IS NOT NULL
            """
        )
        c, mn, mx, avg = cur.fetchone()
        cur.execute(
            f"""
            SELECT COUNT(*) FROM {schema}.PRODUTO_ESPECIFICACAO_TECNICA
            WHERE LENGTH(FOTOPRINCIPAL) = 4912
            """
        )
        n_4912 = cur.fetchone()[0]
        cur.execute(
            f"""
            SELECT COUNT(*) FROM {schema}.PRODUTO_ESPECIFICACAO_TECNICA
            WHERE FOTOPRINCIPAL IS NOT NULL AND LENGTH(FOTOPRINCIPAL) <> 4912
            """
        )
        n_other = cur.fetchone()[0]
        # sample of exactly 4912
        cur.execute(
            f"""
            SELECT IDCODBARPROD, FOTOPRINCIPAL
            FROM {schema}.PRODUTO_ESPECIFICACAO_TECNICA
            WHERE LENGTH(FOTOPRINCIPAL) = 4912
            FETCH FIRST 5 ROWS ONLY
            """
        )
        samples_4912 = []
        for r in cur.fetchall():
            info = detect_magic(bytes(r[1]) if r[1] is not None else b"")
            samples_4912.append({"idcodbarprod": str(r[0]), **info})

        report["fotoprincipal"] = {
            "count_non_null": int(c or 0),
            "len_min": int(mn or 0),
            "len_max": int(mx or 0),
            "len_avg": float(avg or 0),
            "count_len_4912": int(n_4912 or 0),
            "count_len_other": int(n_other or 0),
            "sample_size": len(image_meta),
            "format_distribution": dict(format_dist),
            "length_top": length_dist.most_common(15),
            "samples": image_meta[:25],
            "samples_4912": samples_4912,
        }
        print(
            "FOTOPRINCIPAL non_null=",
            c,
            "4912=",
            n_4912,
            "other=",
            n_other,
            "formats=",
            dict(format_dist),
        )

    # --- OBSESPECIFIC vs PRODUTO descriptions ---
    obse_cmp: list[dict[str, Any]] = []
    if report["tables"]["PRODUTO_ESPECIFICACAO_TECNICA"]["exists"]:
        cur.execute(
            f"""
            SELECT PV.IDPRODUTO, PV.IDSUBPRODUTO,
                   P.DESCRCOMPRODUTO,
                   G.DESCRRESPRODUTO,
                   PET.OBSESPECIFIC
            FROM {schema}.PRODUTO_GRADE G
            JOIN {schema}.PRODUTO P ON P.IDPRODUTO = G.IDPRODUTO
            JOIN {schema}.PRODUTO_ESPECIFICACAO_TECNICA PET
              ON PET.IDCODBARPROD = G.IDCODBARPROD
            JOIN {schema}.PRODUTOS_VIEW PV
              ON PV.IDPRODUTO = G.IDPRODUTO AND PV.IDSUBPRODUTO = G.IDSUBPRODUTO
            WHERE G.FLAGINATIVO = 'F'
              AND PET.OBSESPECIFIC IS NOT NULL
              AND LENGTH(TRIM(PET.OBSESPECIFIC)) > 0
            FETCH FIRST 40 ROWS ONLY
            """
        )
        better = equal = worse = empty = 0
        for r in cur.fetchall():
            desc = (str(r[2] or "").strip())
            commercial = (str(r[3] or "").strip())
            obse = (str(r[4] or "").strip())
            baseline = commercial or desc
            cls = "EMPTY"
            if not obse:
                empty += 1
                cls = "EMPTY"
            elif not baseline:
                better += 1
                cls = "BETTER"
            elif obse.upper() == baseline.upper() or obse.upper() == desc.upper():
                equal += 1
                cls = "EQUAL"
            elif len(obse) >= 8 and not re.fullmatch(r"\d+:\d+", obse) and (
                len(obse) > len(baseline) * 0.6
                or any(ch.isalpha() for ch in obse)
            ):
                # heuristic: looks commercial and different
                if re.search(r"\d{5,}", obse) and len(obse) < 12:
                    worse += 1
                    cls = "WORSE"
                else:
                    better += 1
                    cls = "BETTER"
            else:
                worse += 1
                cls = "WORSE"
            obse_cmp.append(
                {
                    "sku": f"{int(r[0])}:{int(r[1] or 0)}",
                    "description": desc[:60],
                    "commercial_description": commercial[:60] if commercial else None,
                    "obsespecific": obse[:80],
                    "class": cls,
                }
            )
        report["obsespecific"] = {
            "sample_n": len(obse_cmp),
            "BETTER": better,
            "EQUAL": equal,
            "WORSE": worse,
            "EMPTY": empty,
            "samples": obse_cmp[:30],
        }
        print("OBSESPECIFIC", {k: report["obsespecific"][k] for k in ("BETTER", "EQUAL", "WORSE", "EMPTY")})

    # --- PROMOCAO_GESTAO ---
    if report["tables"]["PROMOCAO_GESTAO"]["exists"]:
        colnames = [c["name"] for c in report["tables"]["PROMOCAO_GESTAO"]["columns"]]
        cur.execute(f"SELECT COUNT(*) FROM {schema}.PROMOCAO_GESTAO")
        total = cur.fetchone()[0]
        cur.execute(
            f"SELECT COUNT(*) FROM {schema}.PROMOCAO_GESTAO WHERE FLAGINATIVO='F'"
        ) if "FLAGINATIVO" in colnames else (None,)
        active_flag = None
        if "FLAGINATIVO" in colnames:
            cur.execute(
                f"SELECT COUNT(*) FROM {schema}.PROMOCAO_GESTAO WHERE FLAGINATIVO='F'"
            )
            active_flag = cur.fetchone()[0]

        # discover date columns
        date_cols = [c for c in colnames if "DT" in c or "DATA" in c or "INI" in c or "FIM" in c]
        sample_cols = [
            c
            for c in colnames
            if c
            in {
                "IDPROMOCAO",
                "DESCRPROMOCAO",
                "NOMEPROMOCAO",
                "TITULOPROMOCAO",
                "FLAGINATIVO",
                "IDEMPRESA",
                "DTINICIO",
                "DTFIM",
                "DTINIPROMOCAO",
                "DTFIMPROMOCAO",
                "DTHORAALTERACAO",
                "DTALTERACAO",
                "DTCADASTRO",
            }
            or c in date_cols[:8]
        ]
        sample_cols = list(dict.fromkeys(sample_cols))[:20]
        select_list = ", ".join(sample_cols) if sample_cols else "IDPROMOCAO"
        cur.execute(
            f"""
            SELECT {select_list}
            FROM {schema}.PROMOCAO_GESTAO
            ORDER BY 1 DESC
            FETCH FIRST 15 ROWS ONLY
            """
        )
        samples = []
        for r in cur.fetchall():
            samples.append(
                {
                    sample_cols[i]: (
                        r[i].isoformat()
                        if isinstance(r[i], (datetime, date))
                        else (str(r[i])[:120] if r[i] is not None else None)
                    )
                    for i in range(len(sample_cols))
                }
            )

        # try find currently active by common date fields
        active_query_tried = []
        active_now = []
        today = date.today().isoformat()
        for start_c, end_c in [
            ("DTINICIO", "DTFIM"),
            ("DTINIPROMOCAO", "DTFIMPROMOCAO"),
            ("DTINIVIGENCIA", "DTFIMVIGENCIA"),
            ("DATAINICIO", "DATAFIM"),
        ]:
            if start_c in colnames and end_c in colnames:
                q = f"""
                    SELECT IDPROMOCAO, {start_c}, {end_c}, FLAGINATIVO
                    FROM {schema}.PROMOCAO_GESTAO
                    WHERE FLAGINATIVO = 'F'
                      AND {start_c} <= CURRENT DATE
                      AND {end_c} >= CURRENT DATE
                    FETCH FIRST 10 ROWS ONLY
                """
                active_query_tried.append([start_c, end_c])
                try:
                    cur.execute(q)
                    for r in cur.fetchall():
                        active_now.append(
                            {
                                "IDPROMOCAO": str(r[0]),
                                "start": r[1].isoformat() if r[1] else None,
                                "end": r[2].isoformat() if r[2] else None,
                                "FLAGINATIVO": r[3],
                            }
                        )
                except Exception as exc:  # noqa: BLE001
                    active_query_tried.append({"error": str(exc)[:200]})

        report["promocao_gestao"] = {
            "total": int(total or 0),
            "flaginativo_F": int(active_flag) if active_flag is not None else None,
            "columns": colnames,
            "date_like_columns": date_cols,
            "samples": samples,
            "active_query_tried": active_query_tried,
            "active_now_samples": active_now,
            "audit_date_local": today,
        }
        print("PROMOCAO_GESTAO total=", total, "active_now=", len(active_now), "cols=", colnames[:12])

    # --- PROMOCAO_GESTAO_PRODUTO ---
    if report["tables"]["PROMOCAO_GESTAO_PRODUTO"]["exists"]:
        colnames = [c["name"] for c in report["tables"]["PROMOCAO_GESTAO_PRODUTO"]["columns"]]
        cur.execute(f"SELECT COUNT(*) FROM {schema}.PROMOCAO_GESTAO_PRODUTO")
        total = cur.fetchone()[0]
        # FLAGPRECOMANDATORIO distribution
        flag_dist = {}
        if "FLAGPRECOMANDATORIO" in colnames:
            cur.execute(
                f"""
                SELECT FLAGPRECOMANDATORIO, COUNT(*)
                FROM {schema}.PROMOCAO_GESTAO_PRODUTO
                GROUP BY FLAGPRECOMANDATORIO
                """
            )
            flag_dist = {str(r[0]): int(r[1]) for r in cur.fetchall()}

        # join sample with VALGRAMAENTRADA if possible
        offer_samples = []
        if report["promocao_gestao"].get("active_now_samples"):
            promo_id = report["promocao_gestao"]["active_now_samples"][0]["IDPROMOCAO"]
        else:
            cur.execute(
                f"""
                SELECT IDPROMOCAO FROM {schema}.PROMOCAO_GESTAO
                WHERE FLAGINATIVO='F'
                FETCH FIRST 1 ROW ONLY
                """
            )
            row = cur.fetchone()
            promo_id = str(row[0]) if row else None

        if promo_id:
            cur.execute(
                f"""
                SELECT PGP.IDPROMOCAO, PGP.IDPRODUTO, PGP.IDSUBPRODUTO,
                       CAST(PGP.VALPRECO AS DOUBLE), PGP.FLAGPRECOMANDATORIO, PGP.FLAGINATIVO,
                       CAST(PPV.VALGRAMAENTRADA AS DOUBLE),
                       CAST(PPP.VALPRECOVAREJO AS DOUBLE)
                FROM {schema}.PROMOCAO_GESTAO_PRODUTO PGP
                JOIN {schema}.PRODUTOS_VIEW PPV
                  ON PPV.IDPRODUTO = PGP.IDPRODUTO AND PPV.IDSUBPRODUTO = PGP.IDSUBPRODUTO
                LEFT JOIN {schema}.POLITICA_PRECO_PRODUTO PPP
                  ON PPP.IDPRODUTO = PGP.IDPRODUTO AND PPP.IDSUBPRODUTO = PGP.IDSUBPRODUTO
                 AND PPP.IDEMPRESA = 1
                WHERE PGP.IDPROMOCAO = ?
                  AND PGP.FLAGINATIVO = 'F'
                FETCH FIRST 25 ROWS ONLY
                """,
                promo_id,
            )
            for r in cur.fetchall():
                val = r[3]
                flag = str(r[4] or "").upper()
                gram = r[6]
                effective = None
                calc = "DIRECT"
                if val is not None:
                    if flag == "T" and gram is not None:
                        effective = float(Decimal(str(val)) * Decimal(str(gram)))
                        calc = "WEIGHT_CONVERTED"
                    else:
                        effective = float(Decimal(str(val)))
                offer_samples.append(
                    {
                        "promo": str(r[0]),
                        "sku": f"{int(r[1])}:{int(r[2] or 0)}",
                        "valpreco": float(val) if val is not None else None,
                        "flagprecomandatorio": flag,
                        "valgramaentrada": float(gram) if gram is not None else None,
                        "effective_offer_price": effective,
                        "calculation_type": calc,
                        "regular_price": float(r[7]) if r[7] is not None else None,
                    }
                )

        report["promocao_gestao_produto"] = {
            "total": int(total or 0),
            "columns": colnames,
            "flagprecomandatorio_dist": flag_dist,
            "sample_promo_id": promo_id,
            "offer_samples": offer_samples,
        }
        print(
            "PROMOCAO_GESTAO_PRODUTO total=",
            total,
            "flag_dist=",
            flag_dist,
            "samples=",
            len(offer_samples),
        )

    # --- PRODUTO_CADEIA_PRECO ---
    if report["tables"]["PRODUTO_CADEIA_PRECO"]["exists"]:
        colnames = [c["name"] for c in report["tables"]["PRODUTO_CADEIA_PRECO"]["columns"]]
        cur.execute(f"SELECT COUNT(*) FROM {schema}.PRODUTO_CADEIA_PRECO")
        total = cur.fetchone()[0]
        cur.execute(
            f"""
            SELECT COUNT(*) FROM {schema}.PRODUTO_GRADE
            WHERE IDCADEIAPRECO IS NOT NULL AND FLAGINATIVO='F'
            """
        )
        grades_with_chain = cur.fetchone()[0]
        cur.execute(
            f"""
            SELECT PCP.IDCADEIAPRECO, PCP.DESCRCADEIAPRECO, COUNT(*)
            FROM {schema}.PRODUTO_CADEIA_PRECO PCP
            JOIN {schema}.PRODUTO_GRADE G ON G.IDCADEIAPRECO = PCP.IDCADEIAPRECO
            WHERE G.FLAGINATIVO='F'
            GROUP BY PCP.IDCADEIAPRECO, PCP.DESCRCADEIAPRECO
            ORDER BY COUNT(*) DESC
            FETCH FIRST 15 ROWS ONLY
            """
        )
        chains = [
            {
                "id": str(r[0]),
                "description": str(r[1] or "")[:80],
                "active_skus": int(r[2]),
            }
            for r in cur.fetchall()
        ]
        report["produto_cadeia_preco"] = {
            "total_chains": int(total or 0),
            "active_grades_with_chain": int(grades_with_chain or 0),
            "columns": colnames,
            "top_chains": chains,
        }
        print("CADEIA total=", total, "grades_with=", grades_with_chain, "top=", chains[:3])

    # classifications (heuristic — filled after review in docs)
    report["preliminary_classification"] = {
        "CISS_IMAGE_PATH_SOURCE": "NOT_USABLE",
        "note": "Final BLOB/OFFER/CHAIN gates filled after human/docs review of this JSON",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("WROTE", OUT)
    cn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

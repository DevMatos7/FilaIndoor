"""Quick SYSCAT + LENGTH/HEX audit without fetching unsupported BLOB type -98."""
from __future__ import annotations

import hashlib
import json
import re
import struct
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pyodbc

ENV = Path(__file__).resolve().parents[1] / ".env"
OUT = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "dynamic-retail-content"
    / "reconciliation"
    / "module-5r-ciss-offers-images.json"
)


def parts() -> dict[str, str]:
    text = ENV.read_text(encoding="utf-8")
    m = re.search(r'DB2_CONN_STRING="([^"]+)"', text)
    if not m:
        raise SystemExit("missing DB2_CONN_STRING")
    return {k: v for k, v in (p.split("=", 1) for p in m.group(1).split(";") if "=" in p)}


def connect():
    p = parts()
    cs = (
        f"Driver={{IBM DB2 ODBC DRIVER}};"
        f"Database={p['DATABASE']};"
        f"Hostname={p['HOSTNAME']};"
        f"Port={p['PORT']};"
        f"Protocol=TCPIP;"
        f"Uid={p['UID']};"
        f"Pwd={p['PWD']};"
    )
    return pyodbc.connect(cs, timeout=60)


def magic_from_hex(hexstr: str | None, declared_len: int | None) -> dict:
    if not hexstr:
        return {"format": "EMPTY", "mime": None, "width": None, "height": None, "head_hex": None}
    raw = bytes.fromhex(hexstr)
    fmt, mime, w, h = "UNKNOWN", None, None, None
    if raw[:3] == b"\xff\xd8\xff":
        fmt, mime = "JPEG", "image/jpeg"
    elif raw[:8] == b"\x89PNG\r\n\x1a\n":
        fmt, mime = "PNG", "image/png"
    elif raw[:2] == b"BM":
        fmt, mime = "BMP", "image/bmp"
    elif raw[:4] == b"RIFF":
        fmt, mime = "WEBP?", "image/webp"
    elif raw[:1] in (b"<", b"{") or raw[:5] == b"<?xml":
        fmt, mime = "TEXT/XML", "text/plain"
    return {
        "format": fmt,
        "mime": mime,
        "width": w,
        "height": h,
        "head_hex": raw[:12].hex(),
        "declared_length": declared_len,
        "head_sha_hint": hashlib.sha256(raw).hexdigest()[:12],
    }


def cols(cur, table: str) -> list[dict]:
    cur.execute(
        """
        SELECT COLNAME, TYPENAME, LENGTH, SCALE, NULLS
        FROM SYSCAT.COLUMNS
        WHERE TABSCHEMA='DBA' AND TABNAME=?
        ORDER BY COLNO
        """,
        table,
    )
    return [
        {
            "name": r[0].strip(),
            "type": r[1].strip(),
            "length": int(r[2]) if r[2] is not None else None,
            "scale": int(r[3]) if r[3] is not None else None,
            "nullable": r[4],
        }
        for r in cur.fetchall()
    ]


def main() -> int:
    report: dict = {
        "module": "5R",
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "blob_fetch_note": "pyodbc ODBC type -98 unsupported; used LENGTH + HEX(SUBSTR) for magic",
    }
    cn = connect()
    cur = cn.cursor()
    print("CONNECTED")

    tables = [
        "PRODUTO_ESPECIFICACAO_TECNICA",
        "PROMOCAO_GESTAO",
        "PROMOCAO_GESTAO_PRODUTO",
        "PRODUTO_CADEIA_PRECO",
    ]
    report["tables"] = {}
    for t in tables:
        c = cols(cur, t)
        report["tables"][t] = {"exists": True, "columns": c}
        print(t, [(x["name"], x["type"], x["length"]) for x in c])

    # FOTOPRINCIPAL stats without materializing BLOB
    cur.execute(
        """
        SELECT COUNT(*),
               SUM(CASE WHEN FOTOPRINCIPAL IS NULL THEN 1 ELSE 0 END),
               SUM(CASE WHEN FOTOPRINCIPAL IS NOT NULL THEN 1 ELSE 0 END),
               SUM(CASE WHEN LENGTH(FOTOPRINCIPAL)=4912 THEN 1 ELSE 0 END),
               SUM(CASE WHEN FOTOPRINCIPAL IS NOT NULL AND LENGTH(FOTOPRINCIPAL)<>4912 THEN 1 ELSE 0 END),
               MIN(LENGTH(FOTOPRINCIPAL)),
               MAX(LENGTH(FOTOPRINCIPAL))
        FROM DBA.PRODUTO_ESPECIFICACAO_TECNICA
        """
    )
    row = cur.fetchone()
    report["fotoprincipal"] = {
        "total_rows": int(row[0] or 0),
        "null_count": int(row[1] or 0),
        "non_null_count": int(row[2] or 0),
        "count_len_4912": int(row[3] or 0),
        "count_len_other": int(row[4] or 0),
        "len_min": int(row[5] or 0) if row[5] is not None else None,
        "len_max": int(row[6] or 0) if row[6] is not None else None,
    }
    print("FOTO stats", report["fotoprincipal"])

    # length histogram (top)
    cur.execute(
        """
        SELECT LENGTH(FOTOPRINCIPAL) AS L, COUNT(*) AS C
        FROM DBA.PRODUTO_ESPECIFICACAO_TECNICA
        WHERE FOTOPRINCIPAL IS NOT NULL
        GROUP BY LENGTH(FOTOPRINCIPAL)
        ORDER BY C DESC
        FETCH FIRST 20 ROWS ONLY
        """
    )
    report["fotoprincipal"]["length_histogram_top"] = [
        {"length": int(r[0]), "count": int(r[1])} for r in cur.fetchall()
    ]

    # magic samples: HEX cast to VARCHAR (avoid ODBC -98/-99 LOB materialization)
    samples = []
    cur.execute(
        """
        SELECT IDCODBARPROD, LENGTH(FOTOPRINCIPAL) AS L,
               CAST(HEX(SUBSTR(FOTOPRINCIPAL,1,32)) AS VARCHAR(64)) AS H
        FROM DBA.PRODUTO_ESPECIFICACAO_TECNICA
        WHERE FOTOPRINCIPAL IS NOT NULL
          AND LENGTH(FOTOPRINCIPAL) = 4912
        FETCH FIRST 8 ROWS ONLY
        """
    )
    for r in cur.fetchall():
        info = magic_from_hex(r[2], int(r[1]))
        samples.append({"idcodbarprod": str(r[0]), "bucket": "LEN_4912", **info})

    cur.execute(
        """
        SELECT IDCODBARPROD, LENGTH(FOTOPRINCIPAL) AS L,
               CAST(HEX(SUBSTR(FOTOPRINCIPAL,1,32)) AS VARCHAR(64)) AS H
        FROM DBA.PRODUTO_ESPECIFICACAO_TECNICA
        WHERE FOTOPRINCIPAL IS NOT NULL
          AND LENGTH(FOTOPRINCIPAL) <> 4912
        ORDER BY LENGTH(FOTOPRINCIPAL) DESC
        FETCH FIRST 25 ROWS ONLY
        """
    )
    for r in cur.fetchall():
        info = magic_from_hex(r[2], int(r[1]))
        samples.append({"idcodbarprod": str(r[0]), "bucket": "LEN_OTHER", **info})

    # try decode via CAST to VARCHAR FOR BIT DATA for small images only (<=64k)
    decode_ok = 0
    decode_fail = 0
    decoded = []
    try:
        cur.execute(
            """
            SELECT IDCODBARPROD, LENGTH(FOTOPRINCIPAL),
                   CAST(HEX(SUBSTR(FOTOPRINCIPAL,1,16)) AS VARCHAR(32))
            FROM DBA.PRODUTO_ESPECIFICACAO_TECNICA
            WHERE FOTOPRINCIPAL IS NOT NULL
              AND LENGTH(FOTOPRINCIPAL) BETWEEN 1000 AND 200000
              AND LENGTH(FOTOPRINCIPAL) <> 4912
            FETCH FIRST 12 ROWS ONLY
            """
        )
        for r in cur.fetchall():
            blob = bytes.fromhex(r[2]) if r[2] else b""
            fmt = "UNKNOWN"
            if blob[:3] == b"\xff\xd8\xff":
                fmt = "JPEG"
                decode_ok += 1
            elif blob[:8] == b"\x89PNG\r\n\x1a\n":
                fmt = "PNG"
                decode_ok += 1
            else:
                decode_fail += 1
            decoded.append(
                {
                    "idcodbarprod": str(r[0]),
                    "length": int(r[1]),
                    "format_head": fmt,
                    "head_hex": blob[:8].hex(),
                }
            )
    except Exception as exc:  # noqa: BLE001
        decoded.append({"cast_error": str(exc)[:300]})

    # attempt full small JPEG export via HEX length check for one image (metadata only)
    # Try ibm_db style: get data with SQL_BLOB via fetching as binary using VARCHAR large
    full_decode_trials = []
    try:
        cur.execute(
            """
            SELECT IDCODBARPROD, LENGTH(FOTOPRINCIPAL) AS L
            FROM DBA.PRODUTO_ESPECIFICACAO_TECNICA
            WHERE FOTOPRINCIPAL IS NOT NULL
              AND LENGTH(FOTOPRINCIPAL) BETWEEN 5000 AND 80000
              AND LENGTH(FOTOPRINCIPAL) <> 4912
            ORDER BY LENGTH(FOTOPRINCIPAL)
            FETCH FIRST 5 ROWS ONLY
            """
        )
        candidates = cur.fetchall()
        for cand in candidates:
            idc, ln = str(cand[0]), int(cand[1])
            # fetch as hex in chunks of 4000 chars (=2000 bytes) — expensive but proves decodability
            # Limit to first 64 bytes for classification already done; for dimensions use JPEG SOF via hex chunks
            cur.execute(
                """
                SELECT CAST(HEX(SUBSTR(FOTOPRINCIPAL,1,512)) AS VARCHAR(1024))
                FROM DBA.PRODUTO_ESPECIFICACAO_TECNICA
                WHERE IDCODBARPROD = ?
                """,
                idc,
            )
            hx = cur.fetchone()[0]
            raw = bytes.fromhex(str(hx).strip()) if hx else b""
            w = h = None
            fmt = "UNKNOWN"
            if raw[:3] == b"\xff\xd8\xff":
                fmt = "JPEG"
                i = 2
                while i < len(raw) - 9:
                    if raw[i] != 0xFF:
                        i += 1
                        continue
                    marker = raw[i + 1]
                    if marker in {0xC0, 0xC1, 0xC2} and i + 9 < len(raw):
                        h = struct.unpack(">H", raw[i + 5 : i + 7])[0]
                        w = struct.unpack(">H", raw[i + 7 : i + 9])[0]
                        break
                    if i + 4 > len(raw):
                        break
                    if marker in {0xD8, 0xD9}:
                        i += 2
                        continue
                    seg_len = struct.unpack(">H", raw[i + 2 : i + 4])[0]
                    i += 2 + seg_len
            elif raw[:8] == b"\x89PNG\r\n\x1a\n" and len(raw) >= 24:
                fmt = "PNG"
                w, h = struct.unpack(">II", raw[16:24])
            full_decode_trials.append(
                {
                    "idcodbarprod": idc,
                    "length": ln,
                    "format": fmt,
                    "width": w,
                    "height": h,
                    "decode_success": fmt in {"JPEG", "PNG"} and w and h,
                }
            )
    except Exception as exc:  # noqa: BLE001
        full_decode_trials.append({"error": str(exc)[:300]})

    formats = {}
    for s in samples:
        formats[s["format"]] = formats.get(s["format"], 0) + 1

    report["fotoprincipal"]["samples"] = samples
    report["fotoprincipal"]["format_distribution_sample"] = formats
    report["fotoprincipal"]["cast_head_trials"] = decoded
    report["fotoprincipal"]["dimension_trials"] = full_decode_trials
    report["fotoprincipal"]["decode_ok_heads"] = decode_ok
    report["fotoprincipal"]["decode_fail_heads"] = decode_fail

    # Classify 4912
    f4912 = [s for s in samples if s.get("bucket") == "LEN_4912"]
    report["fotoprincipal"]["rule_4912"] = {
        "hypothesis": "PLACEHOLDER_OR_FIXED_ASSET",
        "sample_formats": [s["format"] for s in f4912],
        "all_same_head": len({s.get("head_hex") for s in f4912}) == 1 if f4912 else None,
        "heads": list({s.get("head_hex") for s in f4912}),
    }

    # OBSESPECIFIC comparison
    cur.execute(
        """
        SELECT G.IDPRODUTO, G.IDSUBPRODUTO,
               P.DESCRCOMPRODUTO,
               G.DESCRRESPRODUTO,
               CAST(PET.OBSESPECIFIC AS VARCHAR(120))
        FROM DBA.PRODUTO_GRADE G
        JOIN DBA.PRODUTO P ON P.IDPRODUTO = G.IDPRODUTO
        JOIN DBA.PRODUTO_ESPECIFICACAO_TECNICA PET ON PET.IDCODBARPROD = G.IDCODBARPROD
        WHERE G.FLAGINATIVO='F'
          AND PET.OBSESPECIFIC IS NOT NULL
          AND LENGTH(TRIM(CAST(PET.OBSESPECIFIC AS VARCHAR(120)))) > 2
        FETCH FIRST 40 ROWS ONLY
        """
    )
    cmp_rows = []
    tallies = {"BETTER": 0, "EQUAL": 0, "WORSE": 0, "EMPTY": 0}
    for r in cur.fetchall():
        desc = str(r[2] or "").strip()
        commercial = str(r[3] or "").strip()
        obse = str(r[4] or "").strip()
        baseline = commercial or desc
        if not obse:
            cls = "EMPTY"
        elif obse.upper() in {baseline.upper(), desc.upper(), commercial.upper()}:
            cls = "EQUAL"
        elif len(obse) >= 6 and any(ch.isalpha() for ch in obse):
            # prefer longer / more human text
            if len(obse) >= max(len(baseline), 8) or (
                baseline.isupper() and not obse.isupper()
            ):
                cls = "BETTER"
            elif len(obse) < len(baseline) * 0.5:
                cls = "WORSE"
            else:
                cls = "BETTER"
        else:
            cls = "WORSE"
        tallies[cls] += 1
        cmp_rows.append(
            {
                "sku": f"{int(r[0])}:{int(r[1] or 0)}",
                "description": desc[:70],
                "commercial_description": commercial[:70] if commercial else None,
                "obsespecific": obse[:90],
                "class": cls,
            }
        )
    report["obsespecific"] = {"sample_n": len(cmp_rows), **tallies, "samples": cmp_rows[:30]}
    print("OBSE", tallies)

    # PROMOCAO_GESTAO
    pg_cols = [c["name"] for c in report["tables"]["PROMOCAO_GESTAO"]["columns"]]
    cur.execute("SELECT COUNT(*) FROM DBA.PROMOCAO_GESTAO")
    total_pg = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM DBA.PROMOCAO_GESTAO WHERE FLAGINATIVO='F'")
    active_pg = cur.fetchone()[0]
    # pick useful columns
    want = [
        c
        for c in pg_cols
        if c
        in {
            "IDPROMOCAO",
            "DESCRPROMOCAO",
            "DESCPROMOCAO",
            "NOMEPROMOCAO",
            "TITULO",
            "FLAGINATIVO",
            "IDEMPRESA",
            "DTINICIO",
            "DTFIM",
            "DTINIPROMOCAO",
            "DTFIMPROMOCAO",
            "DTALTERACAO",
            "DTHORAALTERACAO",
            "DTCADASTRO",
            "DTINIVIGENCIA",
            "DTFIMVIGENCIA",
            "TIPOSTATUS",
            "STATUS",
        }
    ]
    # also include date-like
    for c in pg_cols:
        if ("DT" in c or "DATA" in c) and c not in want:
            want.append(c)
    want = want[:18]
    select_list = ", ".join(want)
    cur.execute(f"SELECT {select_list} FROM DBA.PROMOCAO_GESTAO ORDER BY IDPROMOCAO DESC FETCH FIRST 12 ROWS ONLY")
    samples_pg = []
    for r in cur.fetchall():
        samples_pg.append(
            {
                want[i]: (
                    r[i].isoformat()
                    if isinstance(r[i], (datetime, date))
                    else (None if r[i] is None else str(r[i])[:120])
                )
                for i in range(len(want))
            }
        )

    active_now = []
    date_pairs = [
        ("DTINICIO", "DTFIM"),
        ("DTINIPROMOCAO", "DTFIMPROMOCAO"),
        ("DTINIVIGENCIA", "DTFIMVIGENCIA"),
        ("DATAINICIO", "DATAFIM"),
        ("DTINICIAL", "DTFINAL"),
    ]
    tried = []
    for a, b in date_pairs:
        if a in pg_cols and b in pg_cols:
            tried.append([a, b])
            try:
                cur.execute(
                    f"""
                    SELECT IDPROMOCAO, {a}, {b}, FLAGINATIVO
                    FROM DBA.PROMOCAO_GESTAO
                    WHERE FLAGINATIVO='F'
                      AND {a} <= CURRENT DATE
                      AND {b} >= CURRENT DATE
                    FETCH FIRST 15 ROWS ONLY
                    """
                )
                for r in cur.fetchall():
                    active_now.append(
                        {
                            "IDPROMOCAO": str(r[0]),
                            "start": r[1].isoformat() if r[1] else None,
                            "end": r[2].isoformat() if r[2] else None,
                            "window": f"{a}/{b}",
                        }
                    )
            except Exception as exc:  # noqa: BLE001
                tried.append({"error": str(exc)[:160]})

    report["promocao_gestao"] = {
        "total": int(total_pg or 0),
        "flaginativo_F": int(active_pg or 0),
        "columns": pg_cols,
        "samples": samples_pg,
        "active_query_tried": tried,
        "active_now_samples": active_now,
    }
    print("PROMOCAO_GESTAO", total_pg, "active_flag_F", active_pg, "active_now", len(active_now))

    # PROMOCAO_GESTAO_PRODUTO
    pgp_cols = [c["name"] for c in report["tables"]["PROMOCAO_GESTAO_PRODUTO"]["columns"]]
    cur.execute("SELECT COUNT(*) FROM DBA.PROMOCAO_GESTAO_PRODUTO")
    total_pgp = cur.fetchone()[0]
    flag_dist = {}
    if "FLAGPRECOMANDATORIO" in pgp_cols:
        cur.execute(
            """
            SELECT FLAGPRECOMANDATORIO, COUNT(*)
            FROM DBA.PROMOCAO_GESTAO_PRODUTO
            GROUP BY FLAGPRECOMANDATORIO
            """
        )
        flag_dist = {str(r[0]): int(r[1]) for r in cur.fetchall()}

    promo_id = active_now[0]["IDPROMOCAO"] if active_now else None
    if not promo_id:
        cur.execute(
            "SELECT IDPROMOCAO FROM DBA.PROMOCAO_GESTAO WHERE FLAGINATIVO='F' FETCH FIRST 1 ROW ONLY"
        )
        rr = cur.fetchone()
        promo_id = str(rr[0]) if rr else None

    offer_samples = []
    if promo_id:
        cur.execute(
            """
            SELECT PGP.IDPROMOCAO, PGP.IDPRODUTO, PGP.IDSUBPRODUTO,
                   CAST(PGP.VALPRECO AS DOUBLE),
                   PGP.FLAGPRECOMANDATORIO,
                   PGP.FLAGINATIVO,
                   CAST(PPV.VALGRAMAENTRADA AS DOUBLE),
                   CAST(PPP.VALPRECOVAREJO AS DOUBLE),
                   CASE WHEN PV.IDCADEIAPRECO IS NULL THEN 'NON_CHAIN' ELSE 'CHAIN' END,
                   PV.IDCADEIAPRECO
            FROM DBA.PROMOCAO_GESTAO_PRODUTO PGP
            JOIN DBA.PRODUTOS_VIEW PPV
              ON PPV.IDPRODUTO=PGP.IDPRODUTO AND PPV.IDSUBPRODUTO=PGP.IDSUBPRODUTO
            JOIN DBA.PRODUTO_GRADE PV
              ON PV.IDPRODUTO=PGP.IDPRODUTO AND PV.IDSUBPRODUTO=PGP.IDSUBPRODUTO
            LEFT JOIN DBA.POLITICA_PRECO_PRODUTO PPP
              ON PPP.IDPRODUTO=PGP.IDPRODUTO AND PPP.IDSUBPRODUTO=PGP.IDSUBPRODUTO
             AND PPP.IDEMPRESA=1
            WHERE PGP.IDPROMOCAO=?
              AND PGP.FLAGINATIVO='F'
            FETCH FIRST 30 ROWS ONLY
            """,
            promo_id,
        )
        for r in cur.fetchall():
            val = r[3]
            flag = str(r[4] or "").upper()
            gram = r[6]
            calc = "DIRECT"
            effective = None
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
                    "chain_mode": r[8],
                    "idcadeiapreco": str(r[9]) if r[9] is not None else None,
                }
            )

    report["promocao_gestao_produto"] = {
        "total": int(total_pgp or 0),
        "columns": pgp_cols,
        "flagprecomandatorio_dist": flag_dist,
        "sample_promo_id": promo_id,
        "offer_samples": offer_samples,
    }
    print("PGP", total_pgp, "flag", flag_dist, "offers", len(offer_samples))

    # CADEIA
    cur.execute("SELECT COUNT(*) FROM DBA.PRODUTO_CADEIA_PRECO")
    n_chain = cur.fetchone()[0]
    cur.execute(
        "SELECT COUNT(*) FROM DBA.PRODUTO_GRADE WHERE IDCADEIAPRECO IS NOT NULL AND FLAGINATIVO='F'"
    )
    n_grade_chain = cur.fetchone()[0]
    cur.execute(
        """
        SELECT PCP.IDCADEIAPRECO, PCP.DESCRCADEIAPRECO, COUNT(*)
        FROM DBA.PRODUTO_CADEIA_PRECO PCP
        JOIN DBA.PRODUTO_GRADE G ON G.IDCADEIAPRECO = PCP.IDCADEIAPRECO
        WHERE G.FLAGINATIVO='F'
        GROUP BY PCP.IDCADEIAPRECO, PCP.DESCRCADEIAPRECO
        ORDER BY COUNT(*) DESC
        FETCH FIRST 15 ROWS ONLY
        """
    )
    top_chains = [
        {"id": str(r[0]), "description": str(r[1] or "")[:80], "active_skus": int(r[2])}
        for r in cur.fetchall()
    ]
    report["produto_cadeia_preco"] = {
        "total_chains": int(n_chain or 0),
        "active_grades_with_chain": int(n_grade_chain or 0),
        "columns": [c["name"] for c in report["tables"]["PRODUTO_CADEIA_PRECO"]["columns"]],
        "top_chains": top_chains,
    }
    print("CHAIN", n_chain, n_grade_chain)

    # Coverage: products with usable foto (non-null, not 4912)
    cur.execute(
        """
        SELECT COUNT(DISTINCT G.IDPRODUTO || ':' || G.IDSUBPRODUTO)
        FROM DBA.PRODUTO_GRADE G
        JOIN DBA.PRODUTO_ESPECIFICACAO_TECNICA PET ON PET.IDCODBARPROD = G.IDCODBARPROD
        WHERE G.FLAGINATIVO='F'
          AND PET.FOTOPRINCIPAL IS NOT NULL
          AND LENGTH(PET.FOTOPRINCIPAL) <> 4912
        """
    )
    report["fotoprincipal"]["active_skus_with_non_4912_image"] = int(cur.fetchone()[0] or 0)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("WROTE", OUT)
    cn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Confirm ≥40 POLITICA vs EMP1 Gertec matches for price source-of-truth."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

import pyodbc
from app.core.config import get_settings


def money(v):
    if v is None:
        return None
    try:
        return round(float(str(v).replace(",", ".").strip()), 2)
    except Exception:
        return None


def main() -> None:
    get_settings.cache_clear()
    s = get_settings()
    parts = {k: v for k, v in (p.split("=", 1) for p in s.db2_conn_string.split(";") if "=" in p)}
    cn = pyodbc.connect(
        f"Driver={{{s.db2_odbc_driver}}};Database={parts['DATABASE']};Hostname={parts['HOSTNAME']};"
        f"Port={parts['PORT']};Protocol=TCPIP;Uid={parts['UID']};Pwd={parts['PWD']};",
        timeout=60,
    )
    cur = cn.cursor()
    cur.execute(
        """
        SELECT g.IDPRODUTO, g.IDSUBPRODUTO, TRIM(CAST(g.CODBAR AS VARCHAR(32))),
               CAST(p.VALPRECOVAREJO AS DOUBLE), v.PRECO, TRIM(v.DESCRICAO)
        FROM DBA.POLITICA_PRECO_PRODUTO p
        JOIN DBA.PRODUTO_GRADE g
          ON g.IDPRODUTO=p.IDPRODUTO AND g.IDSUBPRODUTO=p.IDSUBPRODUTO
        JOIN DBA.EMP1_BUSCA_PRECO_GERTEC_VW v
          ON TRIM(v.CODBAR) = TRIM(CAST(g.CODBAR AS VARCHAR(32)))
        WHERE p.IDEMPRESA=1 AND p.VALPRECOVAREJO > 0 AND g.CODBAR IS NOT NULL
        FETCH FIRST 50 ROWS ONLY
        """
    )
    rows = cur.fetchall()
    match = mm = 0
    details = []
    for r in rows:
        pol, ger = money(r[3]), money(r[4])
        ok = pol is not None and ger is not None and abs(pol - ger) < 0.005
        match += int(ok)
        mm += int(not ok)
        details.append(
            {
                "spid": f"{int(r[0])}:{int(r[1])}",
                "codbar": r[2],
                "politica": pol,
                "gertec": ger,
                "result": "MATCH" if ok else "MISMATCH",
                "descricao": str(r[5] or "").strip(),
            }
        )
    out = {
        "compared": len(rows),
        "match": match,
        "mismatch": mm,
        "price_source_status": "CONFIRMED" if match >= 40 and mm == 0 else "PARTIALLY_CONFIRMED",
        "details": details,
    }
    path = REPO / "docs" / "dynamic-retail-content" / "reconciliation" / "gertec-price-truth.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("compared", "match", "mismatch", "price_source_status")}, indent=2))
    cn.close()


if __name__ == "__main__":
    main()

"""Follow-up: 4912 hash equality, weight-flag samples, promo-empresa tables."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pyodbc

ENV = Path(__file__).resolve().parents[1] / ".env"


def main() -> None:
    text = ENV.read_text(encoding="utf-8")
    m = re.search(r'DB2_CONN_STRING="([^"]+)"', text)
    parts = {k: v for k, v in (p.split("=", 1) for p in m.group(1).split(";") if "=" in p)}
    cn = pyodbc.connect(
        f"Driver={{IBM DB2 ODBC DRIVER}};"
        f"Database={parts['DATABASE']};Hostname={parts['HOSTNAME']};Port={parts['PORT']};"
        f"Protocol=TCPIP;Uid={parts['UID']};Pwd={parts['PWD']};",
        timeout=40,
    )
    cur = cn.cursor()
    cur.execute(
        """
        SELECT TABNAME FROM SYSCAT.TABLES
        WHERE TABSCHEMA='DBA'
          AND (TABNAME LIKE '%PROMOCAO%EMP%' OR TABNAME LIKE 'PROMOCAO_GESTAO%')
        ORDER BY 1
        """
    )
    print("promo_related", [r[0].strip() for r in cur.fetchall()])

    cur.execute(
        """
        SELECT PGP.IDPROMOCAO, PGP.IDPRODUTO, PGP.IDSUBPRODUTO,
               CAST(PGP.VALPRECO AS DOUBLE), PGP.FLAGPRECOMANDATORIO,
               CAST(PPV.VALGRAMAENTRADA AS DOUBLE),
               CAST(PPP.VALPRECOVAREJO AS DOUBLE)
        FROM DBA.PROMOCAO_GESTAO_PRODUTO PGP
        JOIN DBA.PROMOCAO_GESTAO PG ON PG.IDPROMOCAO=PGP.IDPROMOCAO
        JOIN DBA.PRODUTOS_VIEW PPV
          ON PPV.IDPRODUTO=PGP.IDPRODUTO AND PPV.IDSUBPRODUTO=PGP.IDSUBPRODUTO
        LEFT JOIN DBA.POLITICA_PRECO_PRODUTO PPP
          ON PPP.IDPRODUTO=PGP.IDPRODUTO AND PPP.IDSUBPRODUTO=PGP.IDSUBPRODUTO
         AND PPP.IDEMPRESA=1
        WHERE PGP.FLAGPRECOMANDATORIO='T' AND PGP.FLAGINATIVO='F'
          AND PG.FLAGINATIVO='F'
          AND PG.DTINIPROMOCAO <= CURRENT DATE AND PG.DTFIMPROMOCAO >= CURRENT DATE
        FETCH FIRST 8 ROWS ONLY
        """
    )
    print("weight_active_samples")
    for r in cur.fetchall():
        val, gram = r[3], r[5]
        eff = (val * gram) if val is not None and gram is not None else None
        print(
            {
                "promo": r[0],
                "sku": f"{r[1]}:{r[2]}",
                "val": val,
                "gram": gram,
                "eff": eff,
                "regular": r[6],
            }
        )

    cur.execute(
        """
        SELECT IDCODBARPROD FROM DBA.PRODUTO_ESPECIFICACAO_TECNICA
        WHERE LENGTH(FOTOPRINCIPAL)=4912
        FETCH FIRST 2 ROWS ONLY
        """
    )
    ids = [str(r[0]) for r in cur.fetchall()]
    hashes = []
    for idc in ids:
        parts_hex: list[str] = []
        # chunk 2000 bytes → 4000 hex chars
        for start in range(1, 4913, 2000):
            cur.execute(
                """
                SELECT CAST(HEX(SUBSTR(FOTOPRINCIPAL, ?, 2000)) AS VARCHAR(4000))
                FROM DBA.PRODUTO_ESPECIFICACAO_TECNICA
                WHERE IDCODBARPROD=?
                """,
                start,
                idc,
            )
            parts_hex.append(str(cur.fetchone()[0] or "").strip())
        hx = "".join(parts_hex)
        hashes.append(hashlib.sha256(bytes.fromhex(hx)).hexdigest())

    cur.execute(
        """
        SELECT COLNAME, TYPENAME FROM SYSCAT.COLUMNS
        WHERE TABSCHEMA='DBA' AND TABNAME='PROMOCAO_GESTAO_EMPRESA'
        ORDER BY COLNO
        """
    )
    print("PROMOCAO_GESTAO_EMPRESA cols", [(r[0].strip(), r[1].strip()) for r in cur.fetchall()])
    print("placeholder_ids", ids)
    print("placeholder_same_sha256", hashes[0] == hashes[1] if len(hashes) == 2 else None)
    print("placeholder_sha256", hashes)
    cn.close()


if __name__ == "__main__":
    main()

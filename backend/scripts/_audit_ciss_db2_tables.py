"""Find core product/price tables and sample columns. Read-only."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pyodbc

ENV = Path(__file__).resolve().parents[1] / ".env"

TARGETS = [
    "PRODUTO",
    "PRODUTO_EMPRESA",
    "PRODUTO_PRECO",
    "PRECO_PRODUTO",
    "PRODUTO_PROMOCAO",
    "PROMOCAO",
    "PROMOCAO_PRODUTO",
    "ESTOQUE_PRODUTO",
    "PRODUTO_ESTOQUE",
    "ESTOQUE",
    "SECAO",
    "GRUPO",
    "SUBGRUPO",
    "EMPRESA",
    "LOCAL_ESTOQUE",
    "PRODUTO_CODIGO_BARRA",
    "CODIGO_BARRA",
    "ESTRUTURA_MERCADOLOGICA",
    "CONFIG_PRECO",
    "PRODUTO_GRADE",
]


def connect():
    text = ENV.read_text(encoding="utf-8")
    m = re.search(r'DB2_CONN_STRING="([^"]+)"', text)
    parts = {k: v for k, v in (p.split("=", 1) for p in m.group(1).split(";") if "=" in p)}
    conn_str = (
        "Driver={IBM DB2 ODBC DRIVER};"
        f"Database={parts['DATABASE']};"
        f"Hostname={parts['HOSTNAME']};"
        f"Port={parts['PORT']};"
        f"Protocol={parts.get('PROTOCOL', 'TCPIP')};"
        f"Uid={parts['UID']};"
        f"Pwd={parts['PWD']};"
    )
    return pyodbc.connect(conn_str, timeout=20), parts.get("SCHEMA", "DBA")


def main() -> int:
    cn, schema = connect()
    cur = cn.cursor()

    # Exact / near names
    cur.execute(
        """
        SELECT TRIM(TABNAME)
        FROM SYSCAT.TABLES
        WHERE TABSCHEMA = ?
          AND (
            TABNAME IN ({})
            OR TABNAME LIKE 'PRODUTO%'
            OR TABNAME LIKE '%_PRECO%'
            OR TABNAME LIKE 'PRECO%'
            OR TABNAME LIKE 'PROMOCAO%'
            OR TABNAME LIKE '%ESTOQUE_PROD%'
            OR TABNAME LIKE 'CODIGO_BARRA%'
            OR TABNAME IN ('SECAO','GRUPO','SUBGRUPO','EMPRESA','LOCAL_ESTOQUE')
          )
        ORDER BY TABNAME
        FETCH FIRST 200 ROWS ONLY
        """.format(",".join("?" for _ in TARGETS)),
        [schema, *TARGETS],
    )
    names = [r[0].strip() for r in cur.fetchall()]
    print("FOUND", len(names))
    for n in names:
        print(n)

    interesting = [
        n
        for n in names
        if n
        in {
            "PRODUTO",
            "PRODUTO_EMPRESA",
            "PRODUTO_PRECO",
            "PRECO_PRODUTO",
            "PROMOCAO",
            "PROMOCAO_PRODUTO",
            "CAMPANHA_PROMOCIONAL",
            "CAMPANHA_PROMOCIONAL_PRODUTO",
            "ESTOQUE_PRODUTO",
            "PRODUTO_ESTOQUE",
            "SECAO",
            "GRUPO",
            "SUBGRUPO",
            "EMPRESA",
            "LOCAL_ESTOQUE",
            "PRODUTO_CODIGO_BARRA",
            "CODIGO_BARRA",
            "CONFIG_PRECO",
        }
        or n.startswith("PRODUTO")
        and ("PRECO" in n or n in {"PRODUTO", "PRODUTO_EMPRESA"})
    ]
    # Prefer short core set
    prefer = [
        "EMPRESA",
        "PRODUTO",
        "PRODUTO_EMPRESA",
        "PRODUTO_PRECO",
        "PRECO_PRODUTO",
        "PROMOCAO",
        "PROMOCAO_PRODUTO",
        "CAMPANHA_PROMOCIONAL",
        "CAMPANHA_PROMOCIONAL_PRODUTO",
        "ESTOQUE_PRODUTO",
        "PRODUTO_ESTOQUE",
        "SECAO",
        "GRUPO",
        "SUBGRUPO",
        "LOCAL_ESTOQUE",
        "PRODUTO_CODIGO_BARRA",
        "CODIGO_BARRA",
    ]
    for table in prefer:
        if table not in names:
            print(f"\n## {table}: NOT PRESENT")
            continue
        print(f"\n## {table}")
        cur.execute(
            """
            SELECT TRIM(COLNAME), TRIM(TYPENAME), LENGTH, SCALE, NULLS
            FROM SYSCAT.COLUMNS
            WHERE TABSCHEMA = ? AND TABNAME = ?
            ORDER BY COLNO
            FETCH FIRST 60 ROWS ONLY
            """,
            schema,
            table,
        )
        cols = cur.fetchall()
        for c in cols:
            print(f"  {c[0]:40} {c[1]:12} L={c[2]} S={c[3]} NULL={c[4]}")
        # count
        try:
            cur.execute(f'SELECT COUNT(*) FROM "{schema}"."{table}"')
            print("  COUNT=", cur.fetchone()[0])
        except Exception as exc:  # noqa: BLE001
            print("  COUNT_FAIL", type(exc).__name__, str(exc)[:120])

    cn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

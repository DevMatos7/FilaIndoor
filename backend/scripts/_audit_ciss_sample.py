"""Sample 3 products with price fields — no secrets."""
from __future__ import annotations

import re
from pathlib import Path

import pyodbc

ENV = Path(__file__).resolve().parents[1] / ".env"


def connect():
    text = ENV.read_text(encoding="utf-8")
    m = re.search(r'DB2_CONN_STRING="([^"]+)"', text)
    parts = {k: v for k, v in (p.split("=", 1) for p in m.group(1).split(";") if "=" in p)}
    conn_str = (
        "Driver={IBM DB2 ODBC DRIVER};"
        f"Database={parts['DATABASE']};Hostname={parts['HOSTNAME']};Port={parts['PORT']};"
        f"Protocol=TCPIP;Uid={parts['UID']};Pwd={parts['PWD']};"
    )
    return pyodbc.connect(conn_str, timeout=20)


def main() -> None:
    cn = connect()
    cur = cn.cursor()
    print("=== EMPRESA sample ===")
    cur.execute(
        """
        SELECT IDEMPRESA, NOMEFANTASIA, RAZAOSOCIAL
        FROM DBA.EMPRESA
        ORDER BY IDEMPRESA
        FETCH FIRST 10 ROWS ONLY
        """
    )
    for r in cur.fetchall():
        print(r)

    print("\n=== PRODUTO_GRADE price sample (active) ===")
    cur.execute(
        """
        SELECT g.IDPRODUTO, g.IDSUBPRODUTO, g.DESCRRESPRODUTO, g.CODBAR,
               g.VALPRECOVAREJO, g.VALPROMVAREJO, g.DTINIPROMOCAO, g.DTFIMPROMOCAO,
               g.FLAGINATIVO, p.EMBALAGEMSAIDA, p.IDSECAO, p.IDGRUPO, p.IDSUBGRUPO,
               p.DESCRCOMPRODUTO
        FROM DBA.PRODUTO_GRADE g
        JOIN DBA.PRODUTO p ON p.IDPRODUTO = g.IDPRODUTO
        WHERE g.FLAGINATIVO = 'F'
          AND g.VALPRECOVAREJO IS NOT NULL
          AND g.VALPRECOVAREJO > 0
        ORDER BY g.DTULTIMAALTERACAO DESC
        FETCH FIRST 5 ROWS ONLY
        """
    )
    for r in cur.fetchall():
        print(r)

    print("\n=== POLITICA_PRECO_PRODUTO columns present? sample ===")
    cur.execute(
        """
        SELECT TRIM(COLNAME)
        FROM SYSCAT.COLUMNS
        WHERE TABSCHEMA='DBA' AND TABNAME='POLITICA_PRECO_PRODUTO'
        ORDER BY COLNO
        FETCH FIRST 40 ROWS ONLY
        """
    )
    print([c[0] for c in cur.fetchall()])

    print("\n=== PRODUTO_GRADE_IMAGENS sample cols ===")
    cur.execute(
        """
        SELECT TRIM(COLNAME)
        FROM SYSCAT.COLUMNS
        WHERE TABSCHEMA='DBA' AND TABNAME='PRODUTO_GRADE_IMAGENS'
        ORDER BY COLNO
        FETCH FIRST 30 ROWS ONLY
        """
    )
    print([c[0] for c in cur.fetchall()])

    print("\n=== PRODUTO_DESCONTO_QTDE sample cols ===")
    cur.execute(
        """
        SELECT TRIM(COLNAME)
        FROM SYSCAT.COLUMNS
        WHERE TABSCHEMA='DBA' AND TABNAME='PRODUTO_DESCONTO_QTDE'
        ORDER BY COLNO
        FETCH FIRST 30 ROWS ONLY
        """
    )
    print([c[0] for c in cur.fetchall()])

    print("\n=== LOCAL_ESTOQUE / saldo view? ===")
    cur.execute(
        """
        SELECT TRIM(TABNAME) FROM SYSCAT.TABLES
        WHERE TABSCHEMA='DBA' AND (
          TABNAME='LOCAL_ESTOQUE'
          OR TABNAME LIKE 'ESTOQUE%PROD%'
          OR TABNAME='PRODUTO_GRADE_SALDO_EST_VW'
          OR TABNAME='PRODUTOS_SALDOS_VIEW'
        )
        ORDER BY TABNAME
        """
    )
    print([r[0] for r in cur.fetchall()])

    cn.close()


if __name__ == "__main__":
    main()

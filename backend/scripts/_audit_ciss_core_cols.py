"""Dump columns for core retail tables only."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pyodbc

ENV = Path(__file__).resolve().parents[1] / ".env"
TABLES = [
    "PRODUTO",
    "PRODUTO_EMPRESA",
    "PRODUTO_GRADE",
    "PRODUTO_PRECO_DIA",
    "PRODUTO_PRECO_DESCONTO",
    "PRODUTO_PRECO_ATACADO",
    "PRODUTO_DESCONTO_QTDE",
    "PROMOCAO",
    "CAMPANHA_PROMOCIONAL",
    "CAMPANHA_PROMOCIONAL_PRODUTO",
    "POLITICA_PRECO_PRODUTO",
    "SECAO",
    "GRUPO",
    "SUBGRUPO",
    "ESTRUTURA_MERCADOLOGICA",
    "PRODUTO_GRADE_IMAGENS",
    "PRODUTO_GRADE_SALDO_EST_VW",
    "LOCAL_ESTOQUE",
]


def connect():
    text = ENV.read_text(encoding="utf-8")
    m = re.search(r'DB2_CONN_STRING="([^"]+)"', text)
    parts = {k: v for k, v in (p.split("=", 1) for p in m.group(1).split(";") if "=" in p)}
    conn_str = (
        "Driver={IBM DB2 ODBC DRIVER};"
        f"Database={parts['DATABASE']};Hostname={parts['HOSTNAME']};Port={parts['PORT']};"
        f"Protocol=TCPIP;Uid={parts['UID']};Pwd={parts['PWD']};"
    )
    return pyodbc.connect(conn_str, timeout=20), parts.get("SCHEMA", "DBA")


def main() -> int:
    cn, schema = connect()
    cur = cn.cursor()
    out = Path(__file__).resolve().parents[2] / "docs" / "dynamic-retail-content" / "_raw_ciss_columns.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for table in TABLES:
        cur.execute(
            "SELECT COUNT(*) FROM SYSCAT.TABLES WHERE TABSCHEMA=? AND TABNAME=?",
            schema,
            table,
        )
        if cur.fetchone()[0] == 0:
            lines.append(f"\n## {table}: NOT PRESENT\n")
            continue
        lines.append(f"\n## {table}\n")
        cur.execute(
            """
            SELECT TRIM(COLNAME), TRIM(TYPENAME), LENGTH, SCALE, NULLS
            FROM SYSCAT.COLUMNS
            WHERE TABSCHEMA=? AND TABNAME=?
            ORDER BY COLNO
            """,
            schema,
            table,
        )
        for c in cur.fetchall():
            lines.append(f"{c[0]}\t{c[1]}\tL={c[2]}\tS={c[3]}\tNULL={c[4]}\n")
        try:
            cur.execute(f'SELECT COUNT(*) FROM "{schema}"."{table}"')
            lines.append(f"COUNT\t{cur.fetchone()[0]}\n")
        except Exception as exc:  # noqa: BLE001
            lines.append(f"COUNT_FAIL\t{type(exc).__name__}\t{str(exc)[:160]}\n")
    out.write_text("".join(lines), encoding="utf-8")
    print("WROTE", out)
    cn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

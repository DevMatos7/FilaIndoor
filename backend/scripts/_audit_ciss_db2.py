"""Read-only CISS DB2 schema audit. Never prints credentials."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pyodbc

ENV = Path(__file__).resolve().parents[1] / ".env"


def load_conn_parts() -> dict[str, str]:
    text = ENV.read_text(encoding="utf-8")
    m = re.search(r'DB2_CONN_STRING="([^"]+)"', text)
    if not m:
        raise SystemExit("DB2_CONN_STRING not found in .env")
    raw = m.group(1)
    return {k: v for k, v in (p.split("=", 1) for p in raw.split(";") if "=" in p)}


def main() -> int:
    parts = load_conn_parts()
    safe = {k: ("***" if k.upper() == "PWD" else v) for k, v in parts.items()}
    print("parts:", safe)

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
    try:
        cn = pyodbc.connect(conn_str, timeout=20)
    except Exception as exc:  # noqa: BLE001
        print("CONNECT_FAIL", type(exc).__name__, str(exc)[:400])
        return 1

    print("CONNECTED")
    cur = cn.cursor()
    schema = parts.get("SCHEMA", "DBA")
    cur.execute(
        """
        SELECT TRIM(TABSCHEMA), TRIM(TABNAME)
        FROM SYSCAT.TABLES
        WHERE TABSCHEMA = ?
          AND (
            UPPER(TABNAME) LIKE '%PROD%'
            OR UPPER(TABNAME) LIKE '%PRECO%'
            OR UPPER(TABNAME) LIKE '%PROMO%'
            OR UPPER(TABNAME) LIKE '%ESTOQ%'
            OR UPPER(TABNAME) LIKE '%SECAO%'
            OR UPPER(TABNAME) LIKE '%EMPRE%'
            OR UPPER(TABNAME) LIKE '%FILIAL%'
            OR UPPER(TABNAME) LIKE '%EAN%'
            OR UPPER(TABNAME) LIKE '%BARRA%'
            OR UPPER(TABNAME) LIKE '%OFERT%'
            OR UPPER(TABNAME) LIKE '%CAD%'
          )
        ORDER BY TABNAME
        FETCH FIRST 120 ROWS ONLY
        """,
        schema,
    )
    rows = cur.fetchall()
    print(f"candidate_tables={len(rows)} schema={schema}")
    for r in rows:
        print(f"{r[0]}.{r[1]}")
    cn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

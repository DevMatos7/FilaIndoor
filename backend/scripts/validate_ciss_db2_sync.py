"""Valida IBM DB2 ODBC + sync real CISS → Postgres (host).

Não imprime senha/DSN completo.
Uso:
  python scripts/validate_ciss_db2_sync.py
  python scripts/validate_ciss_db2_sync.py --company 1 --limit 20
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select, text

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.modules.org.models.entities import Store
from app.modules.queue import models as queue_models  # noqa: F401 — resolve relationship Queue
from app.modules.retail import models as retail_models  # noqa: F401
from app.modules.retail.models import RetailPrice, RetailProduct, RetailStoreSource
from app.modules.retail.providers.ciss_db2 import CissDb2RetailProvider
from app.modules.retail.sync_service import RetailSyncService


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--company", default="1", help="IDEMPRESA CISS")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--store-name", default="", help="filtro opcional do nome da loja app")
    args = parser.parse_args()

    get_settings.cache_clear()
    settings = get_settings()
    print("=== PRECHECK ===")
    print("retail_provider:", settings.retail_provider)
    print("db2_schema:", settings.db2_schema)
    print("db2_conn_configured:", bool(settings.db2_conn_string))
    print("odbc_driver:", settings.db2_odbc_driver)

    try:
        import pyodbc

        drivers = pyodbc.drivers()
        ibm = [d for d in drivers if "IBM DB2" in d.upper()]
        print("ibm_odbc_drivers:", ibm or "NONE")
        if not ibm:
            print("FAIL: instale IBM DB2 ODBC DRIVER no Windows host")
            return 2
    except ImportError:
        print("FAIL: pyodbc não instalado")
        return 2

    if settings.retail_provider != "ciss_db2":
        print("WARN: RETAIL_PROVIDER != ciss_db2 — forçando provider ciss_db2 nesta validação")

    provider = CissDb2RetailProvider()
    if not provider.configured:
        print("FAIL: DB2_CONN_STRING vazio")
        return 2

    print("\n=== CONNECT + SAMPLE FETCH ===")
    t0 = time.perf_counter()
    try:
        products = provider.fetch_products(limit=args.limit)
        elapsed = time.perf_counter() - t0
        print(f"products_fetched={len(products)} elapsed_s={elapsed:.2f}")
        for p in products[:3]:
            print(
                f"  sample product id={p.source_product_id} unit={p.unit} "
                f"section={p.section_name or p.section_code} active={p.active}"
            )
    except Exception as exc:  # noqa: BLE001
        print("FAIL fetch_products:", type(exc).__name__, str(exc)[:240])
        return 3

    t1 = time.perf_counter()
    try:
        prices = provider.fetch_prices(company_code=args.company, limit=args.limit)
        print(f"prices_fetched={len(prices)} elapsed_s={time.perf_counter()-t1:.2f} company={args.company}")
        for p in prices[:3]:
            print(f"  sample price kind={p.price_kind} amount={p.amount} sku={p.source_product_id}")
    except Exception as exc:  # noqa: BLE001
        print("FAIL fetch_prices:", type(exc).__name__, str(exc)[:240])
        return 3

    print("\n=== SYNC → POSTGRES ===")
    db = SessionLocal()
    try:
        # ensure retail tables exist
        db.execute(text("SELECT 1 FROM retail_products LIMIT 1"))
        db.commit()
    except Exception as exc:  # noqa: BLE001
        print("FAIL retail tables missing — rode: alembic upgrade head")
        print(type(exc).__name__, str(exc)[:160])
        db.close()
        return 4

    try:
        stmt = select(Store).order_by(Store.name)
        stores = list(db.scalars(stmt).all())
        if args.store_name:
            stores = [s for s in stores if args.store_name.lower() in s.name.lower()]
        if not stores:
            print("FAIL: nenhuma loja no Postgres")
            return 5
        store = stores[0]
        print(f"using_store id={store.id} name={store.name} tz={store.timezone}")

        svc = RetailSyncService(db, provider=provider)
        # temporarily lower limits for smoke
        settings.retail_sync_product_limit = args.limit
        settings.retail_sync_price_limit = args.limit

        mapping = svc.upsert_store_source(store.id, company_code=str(args.company))
        print("mapping:", mapping)

        t2 = time.perf_counter()
        runs = svc.sync_store(
            store.id,
            entities=["PRODUCT", "PRICE", "PROMOTION", "AVAILABILITY"],
            full=True,
        )
        print(f"sync_elapsed_s={time.perf_counter()-t2:.2f}")
        for r in runs:
            print(
                f"  run entity={r['entity']} status={r['status']} "
                f"read={r['records_read']} ins={r['records_inserted']} "
                f"upd={r['records_updated']} skip={r['records_skipped']} fail={r['records_failed']}"
            )
            if r.get("error_summary"):
                print("    error:", r["error_summary"][:200])

        from sqlalchemy import func

        n_prod = db.scalar(select(func.count()).select_from(RetailProduct)) or 0
        n_price = (
            db.scalar(
                select(func.count())
                .select_from(RetailPrice)
                .where(RetailPrice.store_id == store.id, RetailPrice.active.is_(True))
            )
            or 0
        )
        src = db.scalar(
            select(RetailStoreSource).where(RetailStoreSource.store_id == store.id)
        )
        print("\n=== RESULT ===")
        print(f"retail_products={n_prod}")
        print(f"active_prices_store={n_price}")
        print(f"store_source_company={src.company_code if src else None}")
        ok = all(r["status"] == "SUCCESS" for r in runs) and n_prod > 0 and n_price > 0
        print("VALIDATION:", "PASS" if ok else "FAIL")
        return 0 if ok else 6
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

"""Repair RetailProduct rows whose description equals source_product_id (Module 6 P0)."""
from __future__ import annotations

import json

from sqlalchemy import select

from app.db.session import SessionLocal
from app.modules.queue import models as queue_models  # noqa: F401
from app.modules.retail import models as retail_models  # noqa: F401
from app.modules.retail.models import RetailProduct
from app.modules.retail.providers.ciss_db2 import CissDb2RetailProvider
from app.modules.retail.sync_service import RetailSyncService


def main() -> None:
    db = SessionLocal()
    provider = CissDb2RetailProvider()
    sync = RetailSyncService(db, provider=provider)
    bad = list(
        db.scalars(
            select(RetailProduct).where(
                RetailProduct.active.is_(True),
                RetailProduct.description == RetailProduct.source_product_id,
            )
        ).all()
    )
    print("bad_count", len(bad))
    fixed = failed = 0
    batch = 80
    for i in range(0, len(bad), batch):
        chunk = bad[i : i + batch]
        ids = [p.source_product_id for p in chunk]
        try:
            fetched = {p.source_product_id: p for p in provider.fetch_products_by_ids(ids)}
        except Exception as exc:  # noqa: BLE001
            print("batch_fail", i, type(exc).__name__)
            failed += len(chunk)
            continue
        for prod in chunk:
            canon = fetched.get(prod.source_product_id)
            if not canon or not (canon.description or "").strip():
                # clear banned label so TV skips rather than showing id
                if prod.description == prod.source_product_id:
                    prod.description = ""
                    fixed += 1
                continue
            sync._upsert_product(canon)
            fixed += 1
        db.commit()
        print("progress", i + len(chunk), "/", len(bad), "fixed", fixed)
    print(json.dumps({"fixed": fixed, "failed": failed, "remaining_probe": "run count query"}))


if __name__ == "__main__":
    main()

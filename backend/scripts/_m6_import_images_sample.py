"""Import a sample of CISS images for Module 6 visual proof."""
from __future__ import annotations

import json
import time

from sqlalchemy import select

from app.db.session import SessionLocal
from app.modules.org.models.entities import Store
from app.modules.queue import models as queue_models  # noqa: F401
from app.modules.retail import models as retail_models  # noqa: F401
from app.modules.retail.ciss_image_importer import CissProductImageImporter
from app.modules.retail.providers.ciss_db2 import CissDb2RetailProvider


def main() -> None:
    db = SessionLocal()
    try:
        store = db.scalar(select(Store).where(Store.name.ilike("%Campo Novo%")))
        assert store
        importer = CissProductImageImporter(db, provider=CissDb2RetailProvider())
        t0 = time.perf_counter()
        r1 = importer.import_store_products(store.id, limit=20)
        r1["duration_s"] = round(time.perf_counter() - t0, 3)
        t1 = time.perf_counter()
        r2 = importer.import_store_products(store.id, limit=20)
        r2["duration_s"] = round(time.perf_counter() - t1, 3)
        print(json.dumps({"sync1": r1, "sync2": r2}, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()

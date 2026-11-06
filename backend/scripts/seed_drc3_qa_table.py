"""Seed a persisted PRICE_TABLE for DRC-3 QA (Campo Novo / pilot store).

Usage (host, against local API DB):
  cd backend && python -m scripts.seed_drc3_qa_table
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.db.session import SessionLocal
from app.modules.dynamic_content.content_service import DynamicContentService
from app.modules.dynamic_content.models import DynamicContent, DynamicContentTemplate
from app.modules.dynamic_content.templates import ensure_system_templates
from app.modules.org.models.entities import Store
from datetime import datetime, timezone

from app.modules.retail.models import RetailPrice, RetailProduct, RetailStoreProduct, RetailSyncWatermark


def main() -> None:
    db = SessionLocal()
    try:
        ensure_system_templates(db)
        store = db.scalar(select(Store).where(Store.name.ilike("%Campo Novo%"))) or db.scalar(select(Store))
        if not store:
            raise SystemExit("Nenhuma loja encontrada")
        # Refresh watermarks so snapshot is publishable for QA
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for entity in ("PRODUCT", "PRICE", "PROMOTION", "AVAILABILITY"):
            wm = db.scalar(
                select(RetailSyncWatermark).where(
                    RetailSyncWatermark.store_id == store.id,
                    RetailSyncWatermark.entity == entity,
                )
            )
            if wm:
                wm.last_success_at = now
                wm.last_error_at = None
        db.commit()

        existing = db.scalar(
            select(DynamicContent).where(
                DynamicContent.store_id == store.id,
                DynamicContent.name == "DRC3 QA Açougue — preços do dia",
                DynamicContent.active.is_(True),
            )
        )
        svc = DynamicContentService(db)
        if existing:
            snap = svc.preview(existing.id, store.id)
            print(f"already exists: {existing.id} store={store.name} status={snap.get('status')}")
            return

        tpl = db.scalar(select(DynamicContentTemplate).where(DynamicContentTemplate.slug == "price_table_clean"))
        # Prefer products with store link + regular price + commercial description
        q = (
            select(RetailProduct)
            .join(RetailStoreProduct, RetailStoreProduct.product_id == RetailProduct.id)
            .join(
                RetailPrice,
                (RetailPrice.product_id == RetailProduct.id)
                & (RetailPrice.store_id == store.id)
                & (RetailPrice.price_kind == "REGULAR")
                & (RetailPrice.active.is_(True)),
            )
            .where(
                RetailStoreProduct.store_id == store.id,
                RetailProduct.active.is_(True),
            )
            .limit(40)
        )
        products = [
            p
            for p in db.scalars(q).unique().all()
            if (p.commercial_description or p.description or "").strip()
        ][:12]
        if len(products) < 6:
            raise SystemExit(f"Produtos insuficientes com descrição: {len(products)}")

        created = svc.create_content(
            store.id,
            {
                "name": "DRC3 QA Açougue — preços do dia",
                "selection_mode": "MANUAL",
                "template_id": tpl.id,
                "config": {
                    "title": "Açougue — preços do dia",
                    "items_per_page": 6,
                    "page_duration_seconds": 8,
                    "duration_mode": "FULL_CYCLE",
                },
                "products": [{"product_id": p.id, "position": i} for i, p in enumerate(products[:12])],
            },
        )
        snap = svc.preview(created["id"], store.id)
        print(
            f"created={created['id']} store={store.name} items={snap.get('item_count')} "
            f"pages={snap.get('pagination', {}).get('page_count')} status={snap.get('status')}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()

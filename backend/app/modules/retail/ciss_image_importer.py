"""Import CISS FOTOPRINCIPAL BLOB → MediaAsset + ProductMediaLink(source=CISS)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.retail.models import ProductMediaLink, RetailProduct, utcnow
from app.modules.retail.providers.base import RetailDataProvider
from app.modules.retail.providers.ciss_db2 import CissDb2RetailProvider
from app.modules.signage.models import MediaAsset
from app.modules.signage.storage import checksum, save_bytes

logger = logging.getLogger(__name__)


class CissProductImageImporter:
    def __init__(self, db: Session, provider: RetailDataProvider | None = None):
        self.db = db
        self.provider = provider or CissDb2RetailProvider()

    def import_for_product(self, product_id: str, *, store_id: str) -> dict[str, Any]:
        product = self.db.get(RetailProduct, product_id)
        if not product:
            return {"status": "SKIPPED", "reason": "product_not_found"}

        fetch = getattr(self.provider, "fetch_product_image_blob", None)
        if not callable(fetch):
            return {"status": "SKIPPED", "reason": "provider_no_image"}

        blob = fetch(source_product_id=product.source_product_id, gtin=product.gtin)
        if not blob or not blob.get("bytes"):
            return {"status": "SKIPPED", "reason": "no_usable_image"}

        digest = blob["sha256"]
        # Idempotent: reuse MediaAsset with same checksum in store
        existing_asset = self.db.scalar(
            select(MediaAsset).where(
                MediaAsset.store_id == store_id,
                MediaAsset.checksum == digest,
                MediaAsset.active.is_(True),
            )
        )

        # Manual PRIMARY wins — never overwrite
        manual = self.db.scalar(
            select(ProductMediaLink).where(
                ProductMediaLink.product_id == product_id,
                ProductMediaLink.store_id == store_id,
                ProductMediaLink.source == "MANUAL",
                ProductMediaLink.purpose == "PRIMARY",
                ProductMediaLink.active.is_(True),
            )
        )

        ciss_link = self.db.scalar(
            select(ProductMediaLink).where(
                ProductMediaLink.product_id == product_id,
                ProductMediaLink.store_id == store_id,
                ProductMediaLink.source == "CISS",
                ProductMediaLink.purpose == "PRIMARY",
                ProductMediaLink.active.is_(True),
            )
        )

        if existing_asset and ciss_link and ciss_link.media_asset_id == existing_asset.id:
            return {
                "status": "UNCHANGED",
                "product_id": product_id,
                "media_asset_id": existing_asset.id,
                "sha256": digest,
            }

        if not existing_asset:
            key, _path, public = save_bytes(
                store_id, f"ciss_{product.source_product_id.replace(':', '_')}.jpg", blob["bytes"]
            )
            existing_asset = MediaAsset(
                store_id=store_id,
                name=f"CISS {product.description[:80]}",
                media_type="IMAGE",
                mime_type=blob.get("mime_type") or "image/jpeg",
                original_filename=f"ciss_{digest[:12]}.jpg",
                storage_key=key,
                public_url=public,
                size_bytes=len(blob["bytes"]),
                checksum=digest,
                notes="imported_from_ciss_fotoprincipal",
                active=True,
            )
            self.db.add(existing_asset)
            self.db.flush()

        changed = False
        if ciss_link:
            if ciss_link.media_asset_id != existing_asset.id:
                ciss_link.media_asset_id = existing_asset.id
                ciss_link.updated_at = utcnow()
                changed = True
        else:
            is_primary = manual is None
            ciss_link = ProductMediaLink(
                product_id=product_id,
                store_id=store_id,
                media_asset_id=existing_asset.id,
                purpose="PRIMARY",
                source="CISS",
                is_primary=is_primary,
                verified=True,
                active=True,
            )
            self.db.add(ciss_link)
            changed = True

        self.db.commit()
        if changed and ciss_link.is_primary and not manual:
            try:
                from app.modules.dynamic_content.invalidation_service import DynamicInvalidationService

                DynamicInvalidationService(self.db).invalidate_products(
                    store_id,
                    changed_product_ids=[product_id],
                    change_types=["IMAGE_CHANGED"],
                )
            except Exception:  # noqa: BLE001
                logger.exception("ciss.image.invalidate_failed product=%s", product_id)

        logger.info(
            "ciss.image.imported product=%s asset=%s changed=%s",
            product_id,
            existing_asset.id,
            changed,
        )
        return {
            "status": "UPDATED" if changed else "UNCHANGED",
            "product_id": product_id,
            "media_asset_id": existing_asset.id,
            "sha256": digest,
            "manual_preserved": bool(manual),
        }

    def import_store_products(self, store_id: str, *, limit: int = 100) -> dict[str, Any]:
        """Import images for products already synced (best-effort, capped)."""
        products = list(
            self.db.scalars(select(RetailProduct).where(RetailProduct.active.is_(True)).limit(limit)).all()
        )
        inserted = updated = skipped = failed = 0
        changed_ids: list[str] = []
        for p in products:
            try:
                result = self.import_for_product(p.id, store_id=store_id)
                st = result.get("status")
                if st == "UPDATED":
                    updated += 1
                    changed_ids.append(p.id)
                elif st == "UNCHANGED":
                    skipped += 1
                else:
                    skipped += 1
            except Exception:  # noqa: BLE001
                logger.exception("ciss.image.import_failed product=%s", p.id)
                failed += 1
        return {
            "read": len(products),
            "updated": updated,
            "inserted": inserted,
            "skipped": skipped,
            "failed": failed,
            "changed_product_ids": changed_ids,
        }

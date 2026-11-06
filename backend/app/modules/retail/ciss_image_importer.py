"""Import CISS FOTOPRINCIPAL BLOB → MediaAsset + ProductMediaLink(source=CISS)."""

from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.retail.models import ProductMediaLink, RetailProduct, utcnow
from app.modules.retail.providers.base import RetailDataProvider
from app.modules.retail.providers.ciss_db2 import CissDb2RetailProvider
from app.modules.signage.models import MediaAsset
from app.modules.signage.storage import save_bytes

logger = logging.getLogger(__name__)

_FP_RE = re.compile(r"ciss_fp=([^\s|]+)")


def _parse_fp(notes: str | None) -> str | None:
    if not notes:
        return None
    m = _FP_RE.search(notes)
    return m.group(1) if m else None


def _notes_with_fp(fingerprint: str) -> str:
    return f"imported_from_ciss_fotoprincipal|ciss_fp={fingerprint}"


class CissProductImageImporter:
    def __init__(self, db: Session, provider: RetailDataProvider | None = None):
        self.db = db
        self.provider = provider or CissDb2RetailProvider()

    def import_for_product(self, product_id: str, *, store_id: str) -> dict[str, Any]:
        product = self.db.get(RetailProduct, product_id)
        if not product:
            return {"status": "SKIPPED", "reason": "product_not_found", "blob_reads": 0, "bytes": 0}

        probe = getattr(self.provider, "fetch_product_image_meta", None)
        fetch = getattr(self.provider, "fetch_product_image_blob", None)
        if not callable(fetch):
            return {"status": "SKIPPED", "reason": "provider_no_image", "blob_reads": 0, "bytes": 0}

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

        meta = None
        if callable(probe):
            meta = probe(source_product_id=product.source_product_id, gtin=product.gtin)
            if not meta or not meta.get("usable"):
                reason = (meta or {}).get("reason") or "no_usable_image"
                return {
                    "status": "SKIPPED",
                    "reason": reason,
                    "blob_reads": 0,
                    "bytes": 0,
                    "meta_probes": 1,
                }
            # Incremental: same fingerprint already linked → do NOT read BLOB
            if ciss_link:
                asset = self.db.get(MediaAsset, ciss_link.media_asset_id)
                stored_fp = _parse_fp(asset.notes if asset else None)
                if stored_fp and stored_fp == meta.get("fingerprint") and asset and asset.active:
                    return {
                        "status": "UNCHANGED",
                        "product_id": product_id,
                        "media_asset_id": asset.id,
                        "fingerprint": stored_fp,
                        "blob_reads": 0,
                        "bytes": 0,
                        "meta_probes": 1,
                    }

        blob = fetch(source_product_id=product.source_product_id, gtin=product.gtin)
        if not blob or not blob.get("bytes"):
            return {
                "status": "SKIPPED",
                "reason": "no_usable_image",
                "blob_reads": 1,
                "bytes": 0,
                "meta_probes": 1 if meta is not None else 0,
            }

        digest = blob["sha256"]
        fingerprint = blob.get("fingerprint") or (meta or {}).get("fingerprint") or digest
        byte_len = len(blob["bytes"])

        existing_asset = self.db.scalar(
            select(MediaAsset).where(
                MediaAsset.store_id == store_id,
                MediaAsset.checksum == digest,
                MediaAsset.active.is_(True),
            )
        )

        if existing_asset and ciss_link and ciss_link.media_asset_id == existing_asset.id:
            # refresh fingerprint annotation if missing
            if not _parse_fp(existing_asset.notes):
                existing_asset.notes = _notes_with_fp(str(fingerprint))
                self.db.commit()
            return {
                "status": "UNCHANGED",
                "product_id": product_id,
                "media_asset_id": existing_asset.id,
                "sha256": digest,
                "blob_reads": 1,
                "bytes": byte_len,
                "meta_probes": 1 if meta is not None else 0,
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
                size_bytes=byte_len,
                checksum=digest,
                notes=_notes_with_fp(str(fingerprint)),
                active=True,
            )
            self.db.add(existing_asset)
            self.db.flush()
        else:
            existing_asset.notes = _notes_with_fp(str(fingerprint))

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
            "ciss.image.imported product=%s asset=%s changed=%s blob_reads=1 bytes=%s",
            product_id,
            existing_asset.id,
            changed,
            byte_len,
        )
        return {
            "status": "UPDATED" if changed else "UNCHANGED",
            "product_id": product_id,
            "media_asset_id": existing_asset.id,
            "sha256": digest,
            "manual_preserved": bool(manual),
            "blob_reads": 1,
            "bytes": byte_len,
            "meta_probes": 1 if meta is not None else 0,
        }

    def import_store_products(self, store_id: str, *, limit: int = 100) -> dict[str, Any]:
        """Import images for products already synced (best-effort, capped).

        Prioritizes SKUs without an active store CISS PRIMARY link so coverage
        grows across cycles without re-reading unchanged BLOBs (fingerprint skip).
        """
        linked_ids = set(
            self.db.scalars(
                select(ProductMediaLink.product_id).where(
                    ProductMediaLink.store_id == store_id,
                    ProductMediaLink.source == "CISS",
                    ProductMediaLink.purpose == "PRIMARY",
                    ProductMediaLink.active.is_(True),
                )
            ).all()
        )
        all_active = list(
            self.db.scalars(select(RetailProduct).where(RetailProduct.active.is_(True))).all()
        )
        missing = [p for p in all_active if p.id not in linked_ids]
        already = [p for p in all_active if p.id in linked_ids]
        # Fill gaps first, but always reserve a slice to re-probe linked SKUs
        # (fingerprint meta-only — proves incremental second sync without BLOB re-read).
        lim = max(1, int(limit))
        recheck = min(len(already), max(1, lim // 4) if already else 0)
        fill = lim - recheck
        products = missing[:fill] + already[:recheck]
        if len(products) < lim:
            products = (missing + already)[:lim]
        inserted = updated = skipped = failed = unchanged = 0
        blob_reads = bytes_xfer = meta_probes = placeholders = 0
        changed_ids: list[str] = []
        for p in products:
            try:
                result = self.import_for_product(p.id, store_id=store_id)
                st = result.get("status")
                blob_reads += int(result.get("blob_reads") or 0)
                bytes_xfer += int(result.get("bytes") or 0)
                meta_probes += int(result.get("meta_probes") or 0)
                if result.get("reason") == "placeholder_4912":
                    placeholders += 1
                if st == "UPDATED":
                    updated += 1
                    changed_ids.append(p.id)
                elif st == "UNCHANGED":
                    unchanged += 1
                    skipped += 1
                else:
                    skipped += 1
            except Exception:  # noqa: BLE001
                logger.exception("ciss.image.import_failed product=%s", p.id)
                failed += 1
        return {
            "read": len(products),
            "candidates_missing_ciss": len(missing),
            "candidates_linked": len(already),
            "updated": updated,
            "inserted": inserted,
            "skipped": skipped,
            "unchanged": unchanged,
            "failed": failed,
            "blob_reads": blob_reads,
            "bytes_transferred": bytes_xfer,
            "meta_probes": meta_probes,
            "placeholders_ignored": placeholders,
            "changed_product_ids": changed_ids,
        }

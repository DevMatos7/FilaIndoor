"""Mark affected dynamic snapshots dirty (via data_version) and notify displays."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.dynamic_content.impact_resolver import DynamicContentImpactResolver
from app.modules.dynamic_content.models import DynamicContent, DynamicRenderSnapshot, utcnow
from app.modules.realtime.hub import hub
from app.modules.retail.models import RetailSyncWatermark

logger = logging.getLogger(__name__)


class DynamicInvalidationService:
    def __init__(self, db: Session):
        self.db = db
        self.impact = DynamicContentImpactResolver(db)

    def invalidate_products(
        self,
        store_id: str,
        *,
        changed_product_ids: list[str],
        change_types: list[str],
        section_codes: list[str] | None = None,
        group_codes: list[str] | None = None,
        subgroup_codes: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        affected = self.impact.resolve(
            store_id,
            changed_product_ids=changed_product_ids,
            change_types=change_types,
            section_codes=section_codes,
            group_codes=group_codes,
            subgroup_codes=subgroup_codes,
        )
        if not affected:
            return []

        # Bump store data_version without advancing CISS watermark values:
        # touch PRICE watermark updated_at so ensure_current regenerates lazily.
        self._bump_store_version(store_id)

        version_hint = utcnow().isoformat() + "Z"
        for item in affected:
            cid = item["dynamic_content_id"]
            self._mark_snapshots_stale(cid)
            reason = item.get("reason") or (change_types[0] if change_types else "CHANGED")
            hub.publish(
                store_id,
                "dynamic_content.invalidated",
                {
                    "dynamic_content_id": cid,
                    "reason": reason,
                    "version": version_hint,
                    "store_id": store_id,
                },
            )
            logger.info(
                "dynamic.invalidated store=%s content=%s reason=%s",
                store_id,
                cid,
                reason,
            )
        self.db.commit()
        return affected

    def invalidate_content(
        self, content_id: str, *, store_id: str, reason: str = "MANUAL"
    ) -> dict[str, Any]:
        content = self.db.get(DynamicContent, content_id)
        if not content or content.store_id != store_id:
            from app.core.exceptions import NotFoundError

            raise NotFoundError("conteúdo não encontrado")
        self._bump_store_version(store_id)
        self._mark_snapshots_stale(content_id)
        version_hint = utcnow().isoformat() + "Z"
        hub.publish(
            store_id,
            "dynamic_content.invalidated",
            {
                "dynamic_content_id": content_id,
                "reason": reason,
                "version": version_hint,
                "store_id": store_id,
            },
        )
        self.db.commit()
        logger.info("dynamic.invalidated store=%s content=%s reason=%s", store_id, content_id, reason)
        return {"dynamic_content_id": content_id, "reason": reason, "version": version_hint}

    def _mark_snapshots_stale(self, content_id: str) -> None:
        """Force ensure_current_snapshot to regenerate (do not delete)."""
        rows = list(
            self.db.scalars(
                select(DynamicRenderSnapshot).where(
                    DynamicRenderSnapshot.dynamic_content_id == content_id
                )
            ).all()
        )
        for snap in rows:
            # Poison data_version so it no longer matches current store version
            snap.data_version = f"dirty:{snap.data_version}"
            snap.publishable = False

    def _bump_store_version(self, store_id: str) -> None:
        wm = self.db.scalar(
            select(RetailSyncWatermark).where(
                RetailSyncWatermark.store_id == store_id,
                RetailSyncWatermark.source_system == "CISS",
                RetailSyncWatermark.entity == "PRICE",
            )
        )
        now = utcnow()
        if wm:
            wm.updated_at = now
        else:
            self.db.add(
                RetailSyncWatermark(
                    source_system="CISS",
                    entity="PRICE",
                    store_id=store_id,
                    watermark_value=None,
                    last_success_at=None,
                    updated_at=now,
                )
            )
        self.db.flush()

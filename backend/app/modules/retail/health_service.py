from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.org.models.entities import Store
from app.modules.retail.freshness import classify_freshness, lag_seconds
from app.modules.retail.models import (
    RetailPrice,
    RetailProduct,
    RetailPromotion,
    RetailStoreProduct,
    RetailStoreSource,
    RetailSyncWatermark,
)
from app.modules.retail.timezone_util import validate_iana_timezone


class RetailHealthService:
    def __init__(self, db: Session):
        self.db = db

    def health(self, store_id: str) -> dict[str, Any]:
        store = self.db.get(Store, store_id)
        if not store:
            raise NotFoundError("Loja não encontrada")
        tz_ok = True
        tz_error = None
        try:
            validate_iana_timezone(store.timezone)
        except Exception as exc:  # noqa: BLE001
            tz_ok = False
            tz_error = str(exc)

        source = self.db.scalar(
            select(RetailStoreSource).where(
                RetailStoreSource.store_id == store_id,
                RetailStoreSource.active.is_(True),
            )
        )

        def entity_block(entity: str, count: int) -> dict[str, Any]:
            wm = self.db.scalar(
                select(RetailSyncWatermark).where(
                    RetailSyncWatermark.source_system == "CISS",
                    RetailSyncWatermark.entity == entity,
                    RetailSyncWatermark.store_id == store_id,
                )
            )
            last = wm.last_success_at if wm else None
            failed = bool(wm and wm.last_error_at and (not last or wm.last_error_at > last))
            status = classify_freshness(last, failed=failed).value
            return {
                "entity": entity,
                "count": count,
                "last_success_at": last.isoformat() + "Z" if last else None,
                "last_failure_at": wm.last_error_at.isoformat() + "Z" if wm and wm.last_error_at else None,
                "consecutive_failures": int(wm.consecutive_failures or 0) if wm else 0,
                "lag_seconds": lag_seconds(last),
                "status": status,
            }

        products = self.db.scalar(select(func.count()).select_from(RetailProduct)) or 0
        store_products = (
            self.db.scalar(
                select(func.count()).select_from(RetailStoreProduct).where(RetailStoreProduct.store_id == store_id)
            )
            or 0
        )
        prices = (
            self.db.scalar(
                select(func.count())
                .select_from(RetailPrice)
                .where(RetailPrice.store_id == store_id, RetailPrice.active.is_(True))
            )
            or 0
        )
        promos = (
            self.db.scalar(
                select(func.count())
                .select_from(RetailPromotion)
                .where(RetailPromotion.store_id == store_id, RetailPromotion.active.is_(True))
            )
            or 0
        )

        blocks = [
            entity_block("PRODUCT", int(products)),
            entity_block("PRICE", int(prices)),
            entity_block("PROMOTION", int(promos)),
            entity_block("AVAILABILITY", int(store_products)),
        ]
        statuses = {b["status"] for b in blocks}
        if "FAILED" in statuses:
            overall = "FAILED"
        elif "STALE" in statuses:
            overall = "STALE"
        elif "DEGRADED" in statuses or "UNKNOWN" in statuses:
            overall = "DEGRADED"
        else:
            overall = "FRESH"

        from app.modules.retail.provider_guard import provider_label
        from app.modules.retail.scheduler import scheduler_status

        alerts: list[str] = []
        for b in blocks:
            lag = b.get("lag_seconds")
            if b["status"] == "STALE":
                alerts.append(f"{b['entity']}: dados desatualizados (lag {int(lag or 0)}s)")
            elif b["status"] == "FAILED":
                alerts.append(f"{b['entity']}: falha de sincronização ({b.get('consecutive_failures') or 0} consecutivas)")
            elif b["status"] == "DEGRADED" and lag and lag > 60:
                alerts.append(f"{b['entity']}: sincronização atrasada há {int(lag)}s")

        return {
            "store_id": store_id,
            "store_name": store.name,
            "timezone": store.timezone,
            "timezone_valid": tz_ok,
            "timezone_error": tz_error,
            "source": "CISS",
            "provider_label": provider_label(),
            "mapping": {
                "configured": bool(source),
                "company_code": source.company_code if source else None,
                "location_code": source.location_code if source else None,
            },
            "status": overall if source else "UNKNOWN",
            "entities": blocks,
            "alerts": alerts,
            "scheduler": scheduler_status(),
            "stock_filter": "DISABLED_BY_DESIGN",
            "stock_commercial_source": "NOT_CONFIRMED",
        }

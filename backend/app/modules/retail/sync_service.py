from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.modules.org.models.entities import Store
from app.modules.retail.dto import CanonicalPrice, CanonicalProduct, CanonicalPromotion, CanonicalStoreProduct
from app.modules.retail.freshness import utcnow
from app.modules.retail.models import (
    RetailPrice,
    RetailProduct,
    RetailPromotion,
    RetailStoreProduct,
    RetailStoreSource,
    RetailSyncRun,
    RetailSyncWatermark,
)
from app.modules.retail.provider_guard import assert_retail_provider_safe
from app.modules.retail.providers import get_retail_provider
from app.modules.retail.providers.base import RetailDataProvider
from app.modules.retail.sync_lock import retail_sync_lock
from app.modules.retail.timezone_util import validate_iana_timezone


ENTITIES = ("PRODUCT", "PRICE", "PROMOTION", "AVAILABILITY", "OFFER", "PRODUCT_IMAGE", "PRICE_CHAIN")

ENTITY_CHANGE = {
    "PRODUCT": "PRODUCT_CHANGED",
    "PRICE": "PRICE_CHANGED",
    "PROMOTION": "PROMOTION_CHANGED",
    "AVAILABILITY": "AVAILABILITY_CHANGED",
    "OFFER": "PROMOTION_CHANGED",
    "PRODUCT_IMAGE": "IMAGE_CHANGED",
    "PRICE_CHAIN": "PRODUCT_CHANGED",
}


class RetailSyncService:
    def __init__(self, db: Session, provider: RetailDataProvider | None = None):
        self.db = db
        self.settings = get_settings()
        self.provider = provider or get_retail_provider()

    def upsert_store_source(
        self,
        store_id: str,
        *,
        company_code: str,
        location_code: str | None = None,
        source_system: str = "CISS",
        active: bool = True,
    ) -> dict[str, Any]:
        store = self.db.get(Store, store_id)
        if not store:
            raise NotFoundError("Loja não encontrada")
        validate_iana_timezone(store.timezone)
        company_code = str(company_code).strip()
        if not company_code:
            raise ValidationError("company_code obrigatório")
        row = self.db.scalar(
            select(RetailStoreSource).where(
                RetailStoreSource.store_id == store_id,
                RetailStoreSource.source_system == source_system,
            )
        )
        if row:
            row.company_code = company_code
            row.location_code = location_code
            row.active = active
            row.updated_at = utcnow()
        else:
            row = RetailStoreSource(
                store_id=store_id,
                source_system=source_system,
                company_code=company_code,
                location_code=location_code,
                active=active,
            )
            self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._source_dict(row)

    def get_store_source(self, store_id: str, *, source_system: str = "CISS") -> RetailStoreSource:
        row = self.db.scalar(
            select(RetailStoreSource).where(
                RetailStoreSource.store_id == store_id,
                RetailStoreSource.source_system == source_system,
                RetailStoreSource.active.is_(True),
            )
        )
        if not row:
            raise NotFoundError("Mapeamento loja↔CISS não encontrado")
        return row

    def sync_store(
        self,
        store_id: str,
        *,
        entities: list[str] | None = None,
        full: bool = False,
        trigger: str = "MANUAL",
        skip_invalidation: bool = False,
    ) -> list[dict[str, Any]]:
        assert_retail_provider_safe(for_automation=trigger.upper() == "SCHEDULED")
        store = self.db.get(Store, store_id)
        if not store:
            raise NotFoundError("Loja não encontrada")
        validate_iana_timezone(store.timezone)
        source = self.get_store_source(store_id)
        wanted = [e.upper() for e in (entities or list(ENTITIES))]
        for e in wanted:
            if e not in ENTITIES:
                raise ValidationError(f"entity inválida: {e}")
        results = []
        all_changed: dict[str, set[str]] = {}
        for entity in wanted:
            with retail_sync_lock(self.db, store_id, entity) as acquired:
                if not acquired:
                    results.append(
                        {
                            "store_id": store_id,
                            "entity": entity,
                            "status": "SKIPPED",
                            "trigger": trigger.upper(),
                            "error_summary": "sync já em execução (lock)",
                        }
                    )
                    continue
                result, changed_ids = self._sync_entity(
                    store, source, entity, full=full, trigger=trigger.upper()
                )
                results.append(result)
                if changed_ids:
                    all_changed.setdefault(ENTITY_CHANGE[entity], set()).update(changed_ids)

        if not skip_invalidation and all_changed:
            from app.modules.dynamic_content.invalidation_service import DynamicInvalidationService

            product_ids = sorted({pid for ids in all_changed.values() for pid in ids})
            change_types = list(all_changed.keys())
            DynamicInvalidationService(self.db).invalidate_products(
                store_id,
                changed_product_ids=product_ids,
                change_types=change_types,
            )
        return results

    def _sync_entity(
        self,
        store: Store,
        source: RetailStoreSource,
        entity: str,
        *,
        full: bool,
        trigger: str = "MANUAL",
    ) -> tuple[dict[str, Any], set[str]]:
        store_id = store.id
        wm = self._get_watermark(entity, store_id)
        since = None if full else self._parse_wm(wm.watermark_value if wm else None)
        run = RetailSyncRun(
            source_system="CISS",
            entity=entity,
            store_id=store_id,
            trigger=trigger,
            watermark_before=wm.watermark_value if wm else None,
            status="RUNNING",
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        inserted = updated = skipped = failed = 0
        read = 0
        changed: set[str] = set()
        max_src: datetime | None = since
        try:
            if entity == "PRODUCT":
                products = self.provider.fetch_products(
                    since=since, limit=self.settings.retail_sync_product_limit
                )
                read = len(products)
                for p in products:
                    ins, upd, pid = self._upsert_product(p)
                    inserted += ins
                    updated += upd
                    if pid:
                        changed.add(pid)
                    if p.source_updated_at and (max_src is None or p.source_updated_at > max_src):
                        max_src = p.source_updated_at
                store_rows = self.provider.fetch_store_products(
                    company_code=source.company_code,
                    since=since,
                    limit=self.settings.retail_sync_product_limit,
                )
                read += len(store_rows)
                for sp in store_rows:
                    prod = self._get_product_by_source(sp.source_product_id)
                    if not prod:
                        skipped += 1
                        continue
                    i, u, touched = self._upsert_store_product(
                        store_id, source.company_code, prod.id, sp
                    )
                    inserted += i
                    updated += u
                    if touched:
                        changed.add(prod.id)
            elif entity == "PRICE":
                prices = self.provider.fetch_prices(
                    company_code=source.company_code,
                    since=since,
                    limit=self.settings.retail_sync_price_limit,
                    store_timezone=store.timezone,
                )
                read = len(prices)
                touched: set[str] = set()
                for price in prices:
                    prod = self._ensure_minimal_product(price.source_product_id)
                    if price.source_product_id not in touched:
                        self._deactivate_prices(store_id, prod.id)
                        touched.add(price.source_product_id)
                    i, u = self._upsert_price(store_id, prod.id, price)
                    inserted += i
                    updated += u
                    changed.add(prod.id)
                    if price.source_updated_at and (max_src is None or price.source_updated_at > max_src):
                        max_src = price.source_updated_at
            elif entity == "PROMOTION":
                promos = self.provider.fetch_promotions(
                    company_code=source.company_code,
                    since=since,
                    limit=self.settings.retail_sync_price_limit,
                    store_timezone=store.timezone,
                )
                read = len(promos)
                touched = set()
                for promo in promos:
                    prod = self._ensure_minimal_product(promo.source_product_id)
                    if promo.source_product_id not in touched:
                        self._deactivate_promotions(store_id, prod.id)
                        touched.add(promo.source_product_id)
                    i, u = self._upsert_promotion(store_id, prod.id, promo)
                    inserted += i
                    updated += u
                    changed.add(prod.id)
                    if promo.source_updated_at and (max_src is None or promo.source_updated_at > max_src):
                        max_src = promo.source_updated_at
            elif entity == "AVAILABILITY":
                rows = self.provider.fetch_availability(
                    company_code=source.company_code,
                    since=since,
                    limit=self.settings.retail_sync_product_limit,
                )
                read = len(rows)
                for sp in rows:
                    prod = self._get_product_by_source(sp.source_product_id)
                    if not prod:
                        skipped += 1
                        continue
                    i, u, touched_flag = self._upsert_store_product(
                        store_id, source.company_code, prod.id, sp
                    )
                    inserted += i
                    updated += u
                    if touched_flag:
                        changed.add(prod.id)
            elif entity == "OFFER":
                from app.modules.retail.offer_sync_service import RetailOfferSyncService

                result = RetailOfferSyncService(self.db, provider=self.provider).sync_offers(
                    store_id, company_code=source.company_code
                )
                read = int(result.get("campaigns") or 0)
                inserted = int(result.get("inserted") or 0)
                updated = int(result.get("updated") or 0)
                skipped = int(result.get("skipped") or 0)
                changed.update(result.get("changed_product_ids") or [])
            elif entity == "PRODUCT_IMAGE":
                from app.modules.retail.ciss_image_importer import CissProductImageImporter

                result = CissProductImageImporter(self.db, provider=self.provider).import_store_products(
                    store_id, limit=min(200, int(self.settings.retail_sync_product_limit or 200))
                )
                read = int(result.get("read") or 0)
                inserted = int(result.get("inserted") or 0)
                updated = int(result.get("updated") or 0)
                skipped = int(result.get("skipped") or 0)
                failed = int(result.get("failed") or 0)
                changed.update(result.get("changed_product_ids") or [])
            elif entity == "PRICE_CHAIN":
                from app.modules.retail.offer_sync_service import RetailOfferSyncService

                result = RetailOfferSyncService(self.db, provider=self.provider).sync_price_chains()
                read = int(result.get("read") or 0)
                inserted = int(result.get("inserted") or 0)
                updated = int(result.get("updated") or 0)
                changed.update(result.get("changed_product_ids") or [])

            wm_after = max_src.isoformat() if max_src else (wm.watermark_value if wm else None)
            self._set_watermark(entity, store_id, wm_after, ok=True)
            run.status = "SUCCESS"
            run.records_read = read
            run.records_inserted = inserted
            run.records_updated = updated
            run.records_skipped = skipped
            run.records_failed = failed
            run.watermark_after = wm_after
            run.finished_at = utcnow()
            self.db.commit()
        except Exception as exc:  # noqa: BLE001
            self.db.rollback()
            run = self.db.get(RetailSyncRun, run.id) or run
            run.status = "FAILED"
            run.error_summary = str(exc)[:500]
            run.records_read = read
            run.records_inserted = inserted
            run.records_updated = updated
            run.records_skipped = skipped
            run.records_failed = failed + 1
            run.finished_at = utcnow()
            self.db.add(run)
            self._set_watermark(entity, store_id, wm.watermark_value if wm else None, ok=False)
            self.db.commit()
            raise

        payload = self._run_dict(run)
        payload["changed_product_ids"] = sorted(changed)
        return payload, changed

    def _ensure_minimal_product(self, source_product_id: str) -> RetailProduct:
        existing = self._get_product_by_source(source_product_id)
        if existing:
            return existing
        row = RetailProduct(
            source_system="CISS",
            source_product_id=source_product_id,
            description=source_product_id,
            active=True,
            synced_at=utcnow(),
        )
        self.db.add(row)
        self.db.flush()
        return row

    def _get_product_by_source(self, source_product_id: str) -> RetailProduct | None:
        return self.db.scalar(
            select(RetailProduct).where(
                RetailProduct.source_system == "CISS",
                RetailProduct.source_product_id == source_product_id,
            )
        )

    def _upsert_product(self, p: CanonicalProduct) -> tuple[int, int, str | None]:
        """Returns (inserted, updated, product_id_if_changed)."""
        row = self._get_product_by_source(p.source_product_id)
        now = utcnow()
        if row:
            before = (
                row.description,
                row.commercial_description,
                row.gtin,
                row.unit,
                row.section_code,
                row.group_code,
                row.subgroup_code,
                row.brand,
                row.active,
            )
            row.description = p.description
            row.commercial_description = p.commercial_description
            row.gtin = p.gtin
            row.unit = p.unit
            row.section_code = p.section_code
            row.section_name = p.section_name
            row.group_code = p.group_code
            row.group_name = p.group_name
            row.subgroup_code = p.subgroup_code
            row.subgroup_name = p.subgroup_name
            row.brand = p.brand
            row.active = p.active
            row.source_updated_at = p.source_updated_at
            row.synced_at = now
            row.updated_at = now
            after = (
                row.description,
                row.commercial_description,
                row.gtin,
                row.unit,
                row.section_code,
                row.group_code,
                row.subgroup_code,
                row.brand,
                row.active,
            )
            return 0, 1, row.id if before != after else None
        row = RetailProduct(
            source_system="CISS",
            source_product_id=p.source_product_id,
            description=p.description,
            commercial_description=p.commercial_description,
            gtin=p.gtin,
            unit=p.unit,
            section_code=p.section_code,
            section_name=p.section_name,
            group_code=p.group_code,
            group_name=p.group_name,
            subgroup_code=p.subgroup_code,
            subgroup_name=p.subgroup_name,
            brand=p.brand,
            active=p.active,
            source_updated_at=p.source_updated_at,
            synced_at=now,
        )
        self.db.add(row)
        self.db.flush()
        return 1, 0, row.id

    def _upsert_store_product(
        self, store_id: str, company_code: str, product_id: str, sp: CanonicalStoreProduct
    ) -> tuple[int, int, bool]:
        """Returns (inserted, updated, changed)."""
        row = self.db.scalar(
            select(RetailStoreProduct).where(
                RetailStoreProduct.store_id == store_id,
                RetailStoreProduct.product_id == product_id,
            )
        )
        now = utcnow()
        if row:
            before = (row.sellable, row.available, row.current_stock_qty)
            row.sellable = sp.sellable
            row.available = sp.available
            if sp.stock_qty is not None:
                row.current_stock_qty = sp.stock_qty
            row.source_company_code = company_code
            row.source_updated_at = sp.source_updated_at
            row.synced_at = now
            after = (row.sellable, row.available, row.current_stock_qty)
            return 0, 1, before != after
        self.db.add(
            RetailStoreProduct(
                store_id=store_id,
                product_id=product_id,
                source_company_code=company_code,
                sellable=sp.sellable,
                available=sp.available,
                current_stock_qty=sp.stock_qty,
                source_updated_at=sp.source_updated_at,
                synced_at=now,
            )
        )
        return 1, 0, True

    def _deactivate_prices(self, store_id: str, product_id: str) -> None:
        rows = self.db.scalars(
            select(RetailPrice).where(
                RetailPrice.store_id == store_id,
                RetailPrice.product_id == product_id,
                RetailPrice.active.is_(True),
            )
        ).all()
        for r in rows:
            r.active = False

    def _deactivate_promotions(self, store_id: str, product_id: str) -> None:
        rows = self.db.scalars(
            select(RetailPromotion).where(
                RetailPromotion.store_id == store_id,
                RetailPromotion.product_id == product_id,
                RetailPromotion.active.is_(True),
            )
        ).all()
        for r in rows:
            r.active = False

    def _upsert_price(self, store_id: str, product_id: str, price: CanonicalPrice) -> tuple[int, int]:
        row = RetailPrice(
            store_id=store_id,
            product_id=product_id,
            price_kind=price.price_kind,
            amount=price.amount,
            min_qty=price.min_qty,
            max_qty=price.max_qty,
            unit=price.unit,
            starts_at=price.starts_at,
            expires_at=price.expires_at,
            source_ref=price.source_ref,
            condition_text=price.condition_text,
            active=price.active,
            source_updated_at=price.source_updated_at,
            synced_at=utcnow(),
        )
        self.db.add(row)
        return 1, 0

    def _upsert_promotion(self, store_id: str, product_id: str, promo: CanonicalPromotion) -> tuple[int, int]:
        self.db.add(
            RetailPromotion(
                store_id=store_id,
                product_id=product_id,
                source_promotion_id=promo.source_promotion_id,
                promotion_type=promo.promotion_type,
                promo_amount=promo.promo_amount,
                starts_at=promo.starts_at,
                expires_at=promo.expires_at,
                condition_text=promo.condition_text,
                active=promo.active,
                source_updated_at=promo.source_updated_at,
                synced_at=utcnow(),
            )
        )
        return 1, 0

    def _get_watermark(self, entity: str, store_id: str | None) -> RetailSyncWatermark | None:
        return self.db.scalar(
            select(RetailSyncWatermark).where(
                RetailSyncWatermark.source_system == "CISS",
                RetailSyncWatermark.entity == entity,
                RetailSyncWatermark.store_id == store_id,
            )
        )

    def _set_watermark(self, entity: str, store_id: str | None, value: str | None, *, ok: bool) -> None:
        row = self._get_watermark(entity, store_id)
        now = utcnow()
        if not row:
            row = RetailSyncWatermark(
                source_system="CISS",
                entity=entity,
                store_id=store_id,
                watermark_value=value if ok else None,
                last_success_at=now if ok else None,
                last_error_at=None if ok else now,
                consecutive_failures=0 if ok else 1,
                updated_at=now,
            )
            self.db.add(row)
            return
        if ok:
            row.watermark_value = value
            row.last_success_at = now
            row.consecutive_failures = 0
        else:
            row.last_error_at = now
            row.consecutive_failures = int(row.consecutive_failures or 0) + 1
        row.updated_at = now

    @staticmethod
    def _parse_wm(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _source_dict(row: RetailStoreSource) -> dict[str, Any]:
        return {
            "id": row.id,
            "store_id": row.store_id,
            "source_system": row.source_system,
            "company_code": row.company_code,
            "location_code": row.location_code,
            "active": row.active,
        }

    @staticmethod
    def _run_dict(run: RetailSyncRun) -> dict[str, Any]:
        return {
            "id": run.id,
            "source_system": run.source_system,
            "entity": run.entity,
            "store_id": run.store_id,
            "trigger": getattr(run, "trigger", None) or "MANUAL",
            "status": run.status,
            "started_at": run.started_at.isoformat() + "Z" if run.started_at else None,
            "finished_at": run.finished_at.isoformat() + "Z" if run.finished_at else None,
            "records_read": run.records_read,
            "records_inserted": run.records_inserted,
            "records_updated": run.records_updated,
            "records_skipped": run.records_skipped,
            "records_failed": run.records_failed,
            "watermark_before": run.watermark_before,
            "watermark_after": run.watermark_after,
            "error_summary": run.error_summary,
        }

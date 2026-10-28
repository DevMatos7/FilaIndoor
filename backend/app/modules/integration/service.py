from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.modules.integration.models import (
    ErpProduct,
    ErpProductStoreSnapshot,
    Integration,
    IntegrationSyncRun,
)
from app.modules.integration.providers import get_erp_provider
from app.modules.integration.providers.base import ERPProvider
from app.modules.org.models.entities import Store
from app.modules.queue.models.entities import utcnow


class IntegrationService:
    def __init__(self, db: Session, provider: ERPProvider | None = None):
        self.db = db
        self.settings = get_settings()
        self.provider = provider or get_erp_provider(self.settings.erp_provider)

    def provider_info(self) -> dict[str, Any]:
        return {
            **self.provider.capabilities(),
            "price_sync_minutes": self.settings.erp_price_sync_minutes,
            "stock_sync_minutes": self.settings.erp_stock_sync_minutes,
            "only_in_stock_min_qty": self.settings.erp_only_in_stock_min_qty,
        }

    def list_integrations(self, store_id: str | None = None) -> list[dict[str, Any]]:
        stmt = select(Integration).order_by(Integration.name)
        if store_id:
            stmt = stmt.where(Integration.store_id == store_id)
        return [self._integration_dict(i) for i in self.db.scalars(stmt).all()]

    def ensure_integration(self, store_id: str, *, provider: str | None = None, external_store_id: str | None = None) -> dict[str, Any]:
        store = self.db.get(Store, store_id)
        if not store:
            raise NotFoundError("Loja não encontrada")
        existing = self.db.scalar(select(Integration).where(Integration.store_id == store_id))
        if existing:
            if external_store_id:
                existing.external_store_id = external_store_id
            if provider:
                existing.provider = provider
            self.db.commit()
            self.db.refresh(existing)
            return self._integration_dict(existing)
        row = Integration(
            store_id=store_id,
            provider=(provider or self.settings.erp_provider or "mock"),
            name=f"ERP {store.name}",
            external_store_id=external_store_id or store.external_code,
            active=True,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._integration_dict(row)

    def sync_store(self, store_id: str, *, sync_type: str = "FULL") -> dict[str, Any]:
        store = self.db.get(Store, store_id)
        if not store:
            raise NotFoundError("Loja não encontrada")
        integration = self.ensure_integration(store_id)
        provider = get_erp_provider(integration["provider"])
        self.provider = provider

        run = IntegrationSyncRun(
            integration_id=integration["id"],
            provider=provider.name,
            store_id=store_id,
            sync_type=sync_type,
            status="RUNNING",
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        products_upserted = 0
        snapshots_upserted = 0
        try:
            products = provider.get_products(limit=500)
            for p in products:
                prod = self._upsert_product(provider.name, p)
                products_upserted += 1
                price = provider.get_price(p.external_product_id, store_external_id=integration.get("external_store_id"))
                stock = provider.get_stock(p.external_product_id, store_external_id=integration.get("external_store_id"))
                self._upsert_snapshot(store_id, prod, price, stock)
                snapshots_upserted += 1
            run.status = "SUCCESS"
            run.products_upserted = products_upserted
            run.snapshots_upserted = snapshots_upserted
            run.finished_at = utcnow()
            self.db.commit()
        except Exception as exc:  # noqa: BLE001
            run.status = "FAILED"
            run.error_message = str(exc)[:500]
            run.products_upserted = products_upserted
            run.snapshots_upserted = snapshots_upserted
            run.finished_at = utcnow()
            self.db.commit()
            raise

        return self._run_dict(run)

    def list_products(self, *, provider: str | None = None, q: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        stmt = select(ErpProduct).order_by(ErpProduct.description).limit(min(limit, 500))
        if provider:
            stmt = stmt.where(ErpProduct.provider == provider)
        rows = list(self.db.scalars(stmt).all())
        if q:
            needle = q.strip().lower()
            rows = [
                p
                for p in rows
                if needle in (p.description or "").lower()
                or needle in (p.sku or "").lower()
                or needle in (p.external_product_id or "").lower()
            ]
        return [self._product_dict(p) for p in rows]

    def list_snapshots(self, store_id: str) -> list[dict[str, Any]]:
        rows = self.db.execute(
            select(ErpProductStoreSnapshot, ErpProduct)
            .join(ErpProduct, ErpProduct.id == ErpProductStoreSnapshot.product_id)
            .where(ErpProductStoreSnapshot.store_id == store_id)
            .order_by(ErpProduct.description)
        ).all()
        out = []
        for snap, prod in rows:
            out.append({**self._snapshot_dict(snap), "product": self._product_dict(prod)})
        return out

    def list_sync_runs(self, store_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        stmt = select(IntegrationSyncRun).order_by(IntegrationSyncRun.started_at.desc()).limit(min(limit, 100))
        if store_id:
            stmt = stmt.where(IntegrationSyncRun.store_id == store_id)
        return [self._run_dict(r) for r in self.db.scalars(stmt).all()]

    def get_snapshot_for_external(self, store_id: str, product_external_id: str) -> dict[str, Any] | None:
        prod = self.db.scalar(
            select(ErpProduct).where(ErpProduct.external_product_id == product_external_id)
        )
        if not prod:
            return None
        snap = self.db.scalar(
            select(ErpProductStoreSnapshot).where(
                ErpProductStoreSnapshot.product_id == prod.id,
                ErpProductStoreSnapshot.store_id == store_id,
            )
        )
        if not snap:
            return None
        return {**self._snapshot_dict(snap), "product": self._product_dict(prod)}

    def _upsert_product(self, provider: str, p: Any) -> ErpProduct:
        row = self.db.scalar(
            select(ErpProduct).where(
                ErpProduct.provider == provider,
                ErpProduct.external_product_id == p.external_product_id,
            )
        )
        if not row:
            row = ErpProduct(provider=provider, external_product_id=p.external_product_id, description=p.description)
            self.db.add(row)
        row.sku = p.sku
        row.ean = p.ean
        row.description = p.description
        row.unit = p.unit
        row.section_code = p.section_code
        row.group_code = p.group_code
        row.subgroup_code = p.subgroup_code
        row.payload = p.raw
        row.synced_at = utcnow()
        self.db.flush()
        return row

    def _upsert_snapshot(self, store_id: str, product: ErpProduct, price: Any, stock: Any) -> ErpProductStoreSnapshot:
        row = self.db.scalar(
            select(ErpProductStoreSnapshot).where(
                ErpProductStoreSnapshot.product_id == product.id,
                ErpProductStoreSnapshot.store_id == store_id,
            )
        )
        if not row:
            row = ErpProductStoreSnapshot(product_id=product.id, store_id=store_id)
            self.db.add(row)
        if price:
            row.regular_price = price.regular_price
            row.promo_price = price.promo_price
            row.promo_start = price.promo_start
            row.promo_end = price.promo_end
        if stock:
            row.stock_qty = stock.stock_qty
        row.synced_at = utcnow()
        self.db.flush()
        return row

    def _integration_dict(self, i: Integration) -> dict[str, Any]:
        return {
            "id": i.id,
            "store_id": i.store_id,
            "provider": i.provider,
            "name": i.name,
            "external_store_id": i.external_store_id,
            "active": i.active,
            "config": i.config_json or {},
        }

    def _product_dict(self, p: ErpProduct) -> dict[str, Any]:
        return {
            "id": p.id,
            "provider": p.provider,
            "external_product_id": p.external_product_id,
            "sku": p.sku,
            "ean": p.ean,
            "description": p.description,
            "unit": p.unit,
            "section_code": p.section_code,
            "group_code": p.group_code,
            "subgroup_code": p.subgroup_code,
            "synced_at": p.synced_at.isoformat() + "Z" if p.synced_at else None,
        }

    def _snapshot_dict(self, s: ErpProductStoreSnapshot) -> dict[str, Any]:
        return {
            "id": s.id,
            "product_id": s.product_id,
            "store_id": s.store_id,
            "regular_price": s.regular_price,
            "promo_price": s.promo_price,
            "promo_start": s.promo_start.isoformat() + "Z" if s.promo_start else None,
            "promo_end": s.promo_end.isoformat() + "Z" if s.promo_end else None,
            "stock_qty": s.stock_qty,
            "synced_at": s.synced_at.isoformat() + "Z" if s.synced_at else None,
        }

    def _run_dict(self, r: IntegrationSyncRun) -> dict[str, Any]:
        return {
            "id": r.id,
            "integration_id": r.integration_id,
            "provider": r.provider,
            "store_id": r.store_id,
            "sync_type": r.sync_type,
            "status": r.status,
            "products_upserted": r.products_upserted,
            "snapshots_upserted": r.snapshots_upserted,
            "error_message": r.error_message,
            "started_at": r.started_at.isoformat() + "Z" if r.started_at else None,
            "finished_at": r.finished_at.isoformat() + "Z" if r.finished_at else None,
        }

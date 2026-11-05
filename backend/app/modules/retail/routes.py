from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import (
    RETAIL_CONTENT_ADMIN,
    RETAIL_CONTENT_EDITOR,
    RETAIL_CONTENT_VIEWER,
    RETAIL_DATA_SYNC,
    RETAIL_DATA_VIEWER,
)
from app.db.session import get_db
from app.modules.auth.deps import require_permissions
from app.modules.org.models.entities import User
from app.modules.retail.health_service import RetailHealthService
from app.modules.retail.models import RetailProduct, RetailSyncRun
from app.modules.retail.reconcile_service import RetailReconciliationService
from app.modules.retail.sync_service import RetailSyncService

router = APIRouter(tags=["retail-data"])


class StoreSourceBody(BaseModel):
    store_id: str
    company_code: str
    location_code: str | None = None
    source_system: str = "CISS"
    active: bool = True


class SyncBody(BaseModel):
    store_id: str
    entities: list[str] = Field(default_factory=lambda: ["PRODUCT", "PRICE", "PROMOTION", "AVAILABILITY"])
    full: bool = False


class ReconcileBody(BaseModel):
    store_id: str
    product_ids: list[str]


@router.get("/retail-data/health")
def retail_health(
    store_id: str = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(RETAIL_DATA_VIEWER, RETAIL_CONTENT_VIEWER, RETAIL_CONTENT_ADMIN)),
):
    return RetailHealthService(db).health(store_id)


@router.post("/retail-data/store-sources")
def upsert_store_source(
    body: StoreSourceBody,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(RETAIL_DATA_SYNC, RETAIL_CONTENT_ADMIN, RETAIL_CONTENT_EDITOR)),
):
    return RetailSyncService(db).upsert_store_source(
        body.store_id,
        company_code=body.company_code,
        location_code=body.location_code,
        source_system=body.source_system,
        active=body.active,
    )


@router.post("/retail-data/sync")
def retail_sync(
    body: SyncBody,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(RETAIL_DATA_SYNC, RETAIL_CONTENT_ADMIN)),
):
    return RetailSyncService(db).sync_store(body.store_id, entities=body.entities, full=body.full)


@router.get("/retail-data/sync-runs")
def list_sync_runs(
    store_id: str | None = None,
    entity: str | None = None,
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(RETAIL_DATA_VIEWER, RETAIL_CONTENT_VIEWER, RETAIL_CONTENT_ADMIN)),
):
    stmt = select(RetailSyncRun).order_by(RetailSyncRun.started_at.desc()).limit(limit)
    if store_id:
        stmt = stmt.where(RetailSyncRun.store_id == store_id)
    if entity:
        stmt = stmt.where(RetailSyncRun.entity == entity.upper())
    if status:
        stmt = stmt.where(RetailSyncRun.status == status.upper())
    rows = list(db.scalars(stmt).all())
    return [RetailSyncService._run_dict(r) for r in rows]


@router.post("/retail-data/reconcile")
def retail_reconcile(
    body: ReconcileBody,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(RETAIL_DATA_VIEWER, RETAIL_DATA_SYNC, RETAIL_CONTENT_ADMIN)),
):
    return RetailReconciliationService(db).reconcile(body.store_id, body.product_ids)


def _product_payload(r: RetailProduct) -> dict:
    return {
        "id": r.id,
        "source_product_id": r.source_product_id,
        "description": r.description,
        "commercial_description": r.commercial_description,
        "gtin": r.gtin,
        "unit": r.unit,
        "section_code": r.section_code,
        "section_name": r.section_name,
        "group_code": r.group_code,
        "active": r.active,
        "synced_at": r.synced_at.isoformat() + "Z" if r.synced_at else None,
    }


@router.get("/retail-products")
def list_retail_products(
    store_id: str | None = None,
    q: str | None = None,
    section: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(RETAIL_DATA_VIEWER, RETAIL_CONTENT_VIEWER, RETAIL_CONTENT_ADMIN)),
):
    stmt = select(RetailProduct).order_by(RetailProduct.description).limit(limit)
    if section:
        stmt = stmt.where(RetailProduct.section_code == section)
    rows = list(db.scalars(stmt).all())
    if q:
        needle = q.strip().lower()
        rows = [
            r
            for r in rows
            if needle in (r.description or "").lower()
            or needle in (r.source_product_id or "").lower()
            or needle in (r.gtin or "").lower()
        ]
    return [_product_payload(r) for r in rows]


@router.get("/retail-products/{product_id}")
def get_retail_product(
    product_id: str,
    store_id: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(RETAIL_DATA_VIEWER, RETAIL_CONTENT_VIEWER, RETAIL_CONTENT_ADMIN)),
):
    """Detalhe canônico + preços/promo/estoque da loja (camada entregue à futura UI)."""
    from app.core.exceptions import NotFoundError
    from app.modules.retail.models import RetailPrice, RetailPromotion, RetailStoreProduct

    prod = db.get(RetailProduct, product_id)
    if not prod:
        raise NotFoundError("Produto retail não encontrado")
    payload = _product_payload(prod)
    if store_id:
        prices = list(
            db.scalars(
                select(RetailPrice)
                .where(
                    RetailPrice.store_id == store_id,
                    RetailPrice.product_id == product_id,
                    RetailPrice.active.is_(True),
                )
                .order_by(RetailPrice.price_kind, RetailPrice.min_qty)
            ).all()
        )
        promo = db.scalar(
            select(RetailPromotion).where(
                RetailPromotion.store_id == store_id,
                RetailPromotion.product_id == product_id,
                RetailPromotion.active.is_(True),
            )
        )
        sp = db.scalar(
            select(RetailStoreProduct).where(
                RetailStoreProduct.store_id == store_id,
                RetailStoreProduct.product_id == product_id,
            )
        )
        payload["store_id"] = store_id
        payload["prices"] = [
            {
                "price_kind": p.price_kind,
                "amount": p.amount,
                "min_qty": p.min_qty,
                "condition_text": p.condition_text,
                "starts_at": p.starts_at.isoformat() + "Z" if p.starts_at else None,
                "expires_at": p.expires_at.isoformat() + "Z" if p.expires_at else None,
            }
            for p in prices
        ]
        payload["promotion"] = (
            {
                "promo_amount": promo.promo_amount,
                "starts_at": promo.starts_at.isoformat() + "Z" if promo.starts_at else None,
                "expires_at": promo.expires_at.isoformat() + "Z" if promo.expires_at else None,
                "condition_text": promo.condition_text,
            }
            if promo
            else None
        )
        payload["availability"] = (
            {
                "sellable": sp.sellable,
                "available": sp.available,
                "current_stock_qty": sp.current_stock_qty,
            }
            if sp
            else None
        )
    return payload

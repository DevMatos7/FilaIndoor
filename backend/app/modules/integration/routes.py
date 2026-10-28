from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.permissions import INTEGRATION_ADMIN, INTEGRATION_VIEW, QUEUE_ADMIN, QUEUE_MANAGER, QUEUE_VIEW
from app.db.session import get_db
from app.modules.auth.deps import require_permissions
from app.modules.integration.campaign_service import CampaignService
from app.modules.integration.service import IntegrationService
from app.modules.org.models.entities import User

router = APIRouter(prefix="/integrations", tags=["integrations"])


class EnsureIntegrationBody(BaseModel):
    store_id: str
    provider: str | None = None
    external_store_id: str | None = None


class OfferTemplateBody(BaseModel):
    store_id: str
    name: str
    product_external_id: str
    template_key: str = "oferta_acougue"
    only_in_stock: bool = True
    min_stock_qty: float | None = None


@router.get("/provider")
def provider_info(
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(INTEGRATION_VIEW, INTEGRATION_ADMIN, QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return IntegrationService(db).provider_info()


@router.get("")
def list_integrations(
    store_id: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(INTEGRATION_VIEW, INTEGRATION_ADMIN, QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return IntegrationService(db).list_integrations(store_id=store_id)


@router.post("")
def ensure_integration(
    body: EnsureIntegrationBody,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(INTEGRATION_ADMIN, QUEUE_ADMIN, QUEUE_MANAGER)),
):
    return IntegrationService(db).ensure_integration(
        body.store_id, provider=body.provider, external_store_id=body.external_store_id
    )


@router.post("/sync")
def sync_store(
    store_id: str,
    sync_type: str = "FULL",
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(INTEGRATION_ADMIN, QUEUE_ADMIN, QUEUE_MANAGER)),
):
    return IntegrationService(db).sync_store(store_id, sync_type=sync_type)


@router.get("/products")
def list_products(
    provider: str | None = None,
    q: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(INTEGRATION_VIEW, INTEGRATION_ADMIN, QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return IntegrationService(db).list_products(provider=provider, q=q, limit=limit)


@router.get("/snapshots")
def list_snapshots(
    store_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(INTEGRATION_VIEW, INTEGRATION_ADMIN, QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return IntegrationService(db).list_snapshots(store_id)


@router.get("/sync-runs")
def list_sync_runs(
    store_id: str | None = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(INTEGRATION_VIEW, INTEGRATION_ADMIN, QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return IntegrationService(db).list_sync_runs(store_id=store_id, limit=limit)


@router.get("/offers")
def list_offers(
    store_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(INTEGRATION_VIEW, INTEGRATION_ADMIN, QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return CampaignService(db).list_templates(store_id)


@router.post("/offers")
def create_offer(
    body: OfferTemplateBody,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(INTEGRATION_ADMIN, QUEUE_ADMIN, QUEUE_MANAGER)),
):
    return CampaignService(db).create_template(**body.model_dump())


@router.get("/offers/active")
def active_offers(
    store_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(INTEGRATION_VIEW, INTEGRATION_ADMIN, QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    """Ofertas ativas a partir do snapshot local (para signage — sem hit no CISS)."""
    return CampaignService(db).render_active_for_store(store_id)


@router.get("/offers/{template_id}/render")
def render_offer(
    template_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(INTEGRATION_VIEW, INTEGRATION_ADMIN, QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return CampaignService(db).render(template_id)

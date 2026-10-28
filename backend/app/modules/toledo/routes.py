from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.permissions import DEVICE_ADMIN, DEVICE_VIEW, QUEUE_ADMIN, QUEUE_MANAGER, QUEUE_VIEW
from app.db.session import get_db
from app.modules.auth.deps import require_permissions
from app.modules.org.models.entities import User
from app.modules.toledo.bridge import ToledoBridgeService
from app.modules.toledo.service import ToledoService

router = APIRouter(prefix="/toledo", tags=["toledo"])


class PushTestBody(BaseModel):
    ticket_number: str = "A000"
    counter: str | None = "1"
    department: str | None = "Açougue"


class DiscoveryUpdate(BaseModel):
    environment_name: str | None = None
    mgv_version: str | None = None
    mit_version: str | None = None
    mit_cloud: bool | None = None
    mit_cloud_url: str | None = None
    license_notes: str | None = None
    stores_notes: str | None = None
    players_notes: str | None = None
    api_enabled: bool | None = None
    api_base_url: str | None = None
    auth_type: str | None = None
    integration_key_configured: bool | None = None
    network_notes: str | None = None
    docs_compared: bool | None = None
    confirmed_capabilities: dict | None = None
    notes: str | None = None
    mode_intent: str | None = None


@router.get("/status")
def toledo_status(db: Session = Depends(get_db)):
    """Público na LAN — só flag/modo; sem secrets."""
    return ToledoService(db).status()


@router.get("/discovery")
def get_discovery(
    store_id: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(DEVICE_VIEW, DEVICE_ADMIN, QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    svc = ToledoService(db)
    return {**svc.get_discovery(store_id), "completeness": svc.completeness(store_id)}


@router.put("/discovery")
def put_discovery(
    body: DiscoveryUpdate,
    store_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions(DEVICE_ADMIN, QUEUE_ADMIN, QUEUE_MANAGER)),
):
    svc = ToledoService(db)
    data = body.model_dump(exclude_unset=True)
    updated = svc.update_discovery(data, store_id=store_id, updated_by=user.email)
    return {**updated, "completeness": svc.completeness(store_id)}


@router.get("/adapter")
def adapter_info(
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(DEVICE_VIEW, DEVICE_ADMIN, QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return ToledoBridgeService(db).describe()


@router.post("/adapter/test-push")
def adapter_test_push(
    body: PushTestBody,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(DEVICE_ADMIN, QUEUE_ADMIN, QUEUE_MANAGER)),
):
    result = ToledoBridgeService(db).notify_call_safe(
        ticket_number=body.ticket_number,
        counter=body.counter,
        department=body.department,
    )
    return {
        "ok": result.ok,
        "skipped": result.skipped,
        "provider": result.provider,
        "detail": result.detail,
    }


@router.post("/adapter/sync-history")
def adapter_sync_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(DEVICE_ADMIN, QUEUE_ADMIN, QUEUE_MANAGER)),
):
    return ToledoBridgeService(db).sync_history_safe(limit=limit)

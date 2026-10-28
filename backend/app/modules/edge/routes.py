from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.permissions import DEVICE_ADMIN, DEVICE_VIEW, QUEUE_ADMIN, QUEUE_MANAGER, QUEUE_VIEW
from app.db.session import get_db
from app.modules.auth.deps import require_permissions
from app.modules.edge.service import EdgeService
from app.modules.org.models.entities import User

router = APIRouter(prefix="/edge", tags=["edge"])


class OutboxEventIn(BaseModel):
    event_id: str
    store_id: str
    event_type: str = "GENERIC"
    payload: dict | None = None
    origin_device: str | None = None
    origin_edge: str | None = None
    occurred_at: datetime | None = None


class OutboxBatchIn(BaseModel):
    events: list[OutboxEventIn] = Field(default_factory=list)


@router.get("/health")
def edge_health(db: Session = Depends(get_db)):
    return EdgeService(db).health()


@router.get("/snapshot")
def edge_snapshot(
    store_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(DEVICE_VIEW, DEVICE_ADMIN, QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return EdgeService(db).snapshot(store_id)


@router.get("/sync/status")
def edge_sync_status(
    store_id: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(DEVICE_VIEW, DEVICE_ADMIN, QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return EdgeService(db).sync_status(store_id=store_id)


@router.get("/outbox")
def list_outbox(
    store_id: str | None = None,
    sync_status: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(DEVICE_VIEW, DEVICE_ADMIN, QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return EdgeService(db).list_events(store_id=store_id, sync_status=sync_status, limit=limit)


@router.post("/outbox")
def push_outbox(
    body: OutboxBatchIn,
    db: Session = Depends(get_db),
):
    """Aceita eventos do cliente/edge (idempotente por event_id). Sem auth — devices LAN."""
    if not body.events:
        return {"accepted": 0, "events": []}
    return EdgeService(db).enqueue_many([e.model_dump() for e in body.events])


@router.post("/sync")
def flush_sync(
    store_id: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(DEVICE_ADMIN, QUEUE_ADMIN, QUEUE_MANAGER)),
):
    return EdgeService(db).flush(store_id=store_id, limit=limit)


@router.post("/sync/retry")
def retry_sync(
    store_id: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(DEVICE_ADMIN, QUEUE_ADMIN, QUEUE_MANAGER)),
):
    return EdgeService(db).retry_failed(store_id=store_id)

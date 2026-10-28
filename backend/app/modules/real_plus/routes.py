from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.permissions import QUEUE_ADMIN, QUEUE_MANAGER, QUEUE_VIEW
from app.db.session import get_db
from app.modules.auth.deps import get_idempotency_key, require_permissions
from app.modules.org.models.entities import User
from app.modules.real_plus.service import RealPlusService
from app.modules.queue.services.events import publish_queue_event

router = APIRouter(prefix="/real-plus", tags=["real-plus"])


class IssueBody(BaseModel):
    type: str = "NORMAL"
    customer_label: str | None = None
    notify_when_ahead: int = Field(default=2, ge=0, le=20)


class SubscribeBody(BaseModel):
    endpoint: str | None = "stub://browser"


@router.get("/queues/{queue_id}/preview")
def preview(queue_id: str, db: Session = Depends(get_db)):
    return RealPlusService(db).preview(queue_id)


@router.post("/queues/{queue_id}/tickets", status_code=201)
def issue(
    queue_id: str,
    body: IssueBody,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Depends(get_idempotency_key),
):
    result = RealPlusService(db).issue(
        queue_id,
        ticket_type=body.type,
        customer_label=body.customer_label,
        notify_when_ahead=body.notify_when_ahead,
        idempotency_key=idempotency_key,
    )
    try:
        publish_queue_event(db, queue_id=queue_id, event="ticket.created", ticket=result["ticket"])
        publish_queue_event(db, queue_id=queue_id, event="queue.updated")
    except Exception:
        pass
    return result


@router.get("/track/{tracking_token}")
def track(tracking_token: str, db: Session = Depends(get_db)):
    return RealPlusService(db).tracking(tracking_token)


@router.post("/track/{tracking_token}/check-in")
def check_in(tracking_token: str, db: Session = Depends(get_db)):
    return RealPlusService(db).check_in(tracking_token)


@router.post("/track/{tracking_token}/subscribe")
def subscribe(tracking_token: str, body: SubscribeBody, db: Session = Depends(get_db)):
    return RealPlusService(db).subscribe_push(tracking_token, endpoint=body.endpoint)


@router.get("/virtual-tickets")
def list_virtual(
    queue_id: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return RealPlusService(db).list_virtual(queue_id=queue_id, limit=limit)

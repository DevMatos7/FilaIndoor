from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import QUEUE_ADMIN, QUEUE_MANAGER, QUEUE_OPERATOR, QUEUE_VIEW
from app.db.session import get_db
from app.modules.auth.deps import get_idempotency_key, require_permissions
from app.modules.org.models.entities import User
from app.modules.queue.schemas.ticket import (
    CallNextRequest,
    CreateTicketRequest,
    QueueCreateRequest,
    QueueUpdateRequest,
    TicketActionRequest,
)
from app.modules.queue.services.events import publish_queue_event
from app.modules.queue.services.queue_service import QueueService

router = APIRouter(tags=["queues"])


def _toledo_notify_safe(db: Session, ticket: dict) -> None:
    """Side-effect Toledo — nunca falha a chamada nativa."""
    try:
        from app.modules.toledo.bridge import ToledoBridgeService

        ToledoBridgeService(db).notify_call_safe(
            ticket_number=str(ticket.get("number") or ticket.get("display_number") or ""),
            counter=ticket.get("terminal_id"),
            department=ticket.get("department_name"),
        )
    except Exception:
        pass


@router.get("/queues")
def list_queues(
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN, QUEUE_OPERATOR)),
):
    service = QueueService(db)
    queues = service.list_queues()
    return [
        {
            "id": q.id,
            "department_id": q.department_id,
            "name": q.name,
            "status": q.status,
            "priority_strategy": q.priority_strategy,
            "normal_prefix": q.normal_prefix,
            "priority_prefix": q.priority_prefix,
        }
        for q in queues
    ]


@router.post("/queues", status_code=201)
def create_queue(
    body: QueueCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(QUEUE_ADMIN, QUEUE_MANAGER)),
):
    service = QueueService(db)
    queue = service.create_queue(**body.model_dump())
    return {"id": queue.id, "name": queue.name, "status": queue.status}


@router.get("/queues/{queue_id}")
def get_queue(
    queue_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN, QUEUE_OPERATOR)),
):
    service = QueueService(db)
    return service.queue_status(queue_id)


@router.patch("/queues/{queue_id}")
def patch_queue(
    queue_id: str,
    body: QueueUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(QUEUE_ADMIN, QUEUE_MANAGER)),
):
    service = QueueService(db)
    service.update_queue(queue_id, **body.model_dump(exclude_unset=True))
    return service.queue_settings(queue_id)


@router.get("/queues/{queue_id}/status")
def queue_status(
    queue_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN, QUEUE_OPERATOR)),
):
    return QueueService(db).queue_status(queue_id)


@router.get("/queues/{queue_id}/waiting")
def queue_waiting(
    queue_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN, QUEUE_OPERATOR)),
):
    return QueueService(db).waiting_list(queue_id)


@router.get("/queues/{queue_id}/settings")
def queue_settings(
    queue_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return QueueService(db).queue_settings(queue_id)


@router.get("/tickets")
def list_tickets_history(
    queue_id: str | None = None,
    status: str | None = None,
    ticket_type: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN, QUEUE_OPERATOR)),
):
    return QueueService(db).list_history(
        queue_id=queue_id,
        status=status,
        ticket_type=ticket_type,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.post("/queues/{queue_id}/tickets", status_code=201)
def create_ticket(
    queue_id: str,
    body: CreateTicketRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(QUEUE_OPERATOR, QUEUE_MANAGER, QUEUE_ADMIN, QUEUE_VIEW)),
    idempotency_key: str | None = Depends(get_idempotency_key),
):
    ticket = QueueService(db).create_ticket(
        queue_id,
        ticket_type=body.type.upper(),
        source=body.source.upper(),
        idempotency_key=idempotency_key,
    )
    publish_queue_event(db, queue_id=queue_id, event="ticket.created", ticket=ticket)
    publish_queue_event(db, queue_id=queue_id, event="queue.updated")
    return ticket


@router.post("/queues/{queue_id}/next")
def call_next(
    queue_id: str,
    body: CallNextRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions(QUEUE_OPERATOR, QUEUE_MANAGER, QUEUE_ADMIN)),
    idempotency_key: str | None = Depends(get_idempotency_key),
):
    ticket = QueueService(db).call_next(
        queue_id,
        terminal_id=body.terminal_id,
        operator_id=body.operator_id or user.id,
        idempotency_key=idempotency_key,
        auto_complete_current=body.auto_complete_current,
        auto_start=body.auto_start,
    )
    publish_queue_event(db, queue_id=queue_id, event="ticket.called", ticket=ticket)
    publish_queue_event(db, queue_id=queue_id, event="queue.updated")
    _toledo_notify_safe(db, ticket)
    return ticket


@router.get("/tickets/{ticket_id}")
def ticket_detail(
    ticket_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN, QUEUE_OPERATOR)),
):
    return QueueService(db).ticket_detail(ticket_id)


@router.post("/tickets/{ticket_id}/recall")
def recall(
    ticket_id: str,
    body: TicketActionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions(QUEUE_OPERATOR, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    ticket = QueueService(db).recall(
        ticket_id,
        operator_id=body.operator_id or user.id,
        terminal_id=body.terminal_id,
    )
    publish_queue_event(db, queue_id=ticket["queue_id"], event="ticket.recalled", ticket=ticket)
    _toledo_notify_safe(db, ticket)
    return ticket


@router.post("/tickets/{ticket_id}/start")
def start(
    ticket_id: str,
    body: TicketActionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions(QUEUE_OPERATOR, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    ticket = QueueService(db).start(
        ticket_id,
        operator_id=body.operator_id or user.id,
        terminal_id=body.terminal_id,
    )
    publish_queue_event(db, queue_id=ticket["queue_id"], event="ticket.started", ticket=ticket)
    publish_queue_event(db, queue_id=ticket["queue_id"], event="queue.updated")
    return ticket


@router.post("/tickets/{ticket_id}/complete")
def complete(
    ticket_id: str,
    body: TicketActionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions(QUEUE_OPERATOR, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    ticket = QueueService(db).complete(
        ticket_id,
        operator_id=body.operator_id or user.id,
        terminal_id=body.terminal_id,
    )
    publish_queue_event(db, queue_id=ticket["queue_id"], event="ticket.completed", ticket=ticket)
    publish_queue_event(db, queue_id=ticket["queue_id"], event="queue.updated")
    return ticket


@router.post("/tickets/{ticket_id}/no-show")
def no_show(
    ticket_id: str,
    body: TicketActionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions(QUEUE_OPERATOR, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    ticket = QueueService(db).no_show(
        ticket_id,
        operator_id=body.operator_id or user.id,
        terminal_id=body.terminal_id,
    )
    publish_queue_event(db, queue_id=ticket["queue_id"], event="ticket.no_show", ticket=ticket)
    publish_queue_event(db, queue_id=ticket["queue_id"], event="queue.updated")
    return ticket


@router.post("/tickets/{ticket_id}/cancel")
def cancel(
    ticket_id: str,
    body: TicketActionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions(QUEUE_OPERATOR, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    ticket = QueueService(db).cancel(ticket_id, operator_id=body.operator_id or user.id)
    publish_queue_event(db, queue_id=ticket["queue_id"], event="ticket.cancelled", ticket=ticket)
    publish_queue_event(db, queue_id=ticket["queue_id"], event="queue.updated")
    return ticket

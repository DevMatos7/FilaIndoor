from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.session import get_db
from app.modules.auth.deps import get_idempotency_key
from app.modules.org.models.entities import Department, Store
from app.modules.printing.service import PrintService, get_printer_provider
from sqlalchemy import select

from app.modules.queue.models.entities import IdempotencyRecord, Queue, Ticket
from app.modules.queue.services.events import publish_queue_event
from app.modules.queue.services.queue_service import QueueService

router = APIRouter(prefix="/kiosk", tags=["kiosk"])


class KioskIssueRequest(BaseModel):
    type: str = Field(default="NORMAL", description="NORMAL | PRIORITY")
    source: str = Field(default="KIOSK")


def _require_kiosk(queue_id: str, token: str | None, db: Session) -> Queue:
    queue = db.get(Queue, queue_id)
    if not queue:
        raise NotFoundError("Fila não encontrada")
    if not queue.kiosk_enabled:
        raise ForbiddenError("Totem desabilitado para esta fila")
    if not queue.kiosk_token or token != queue.kiosk_token:
        raise ForbiddenError("Token do totem inválido")
    return queue


def _context(db: Session, queue: Queue) -> tuple[str, str]:
    dept = db.get(Department, queue.department_id)
    store_name = "REAL SUPERMERCADO"
    dept_name = queue.department_display_name or (dept.name if dept else queue.name)
    if dept:
        store = db.get(Store, dept.store_id)
        if store:
            store_name = store.name.upper()
    return store_name, dept_name


@router.get("/{queue_id}/status")
def kiosk_status(
    queue_id: str,
    db: Session = Depends(get_db),
    x_kiosk_token: str | None = Header(default=None, alias="X-Kiosk-Token"),
):
    queue = _require_kiosk(queue_id, x_kiosk_token, db)
    status = QueueService(db).queue_status(queue_id)
    _, dept_name = _context(db, queue)
    dept = db.get(Department, queue.department_id)
    status["department_name"] = dept_name
    status["store_id"] = dept.store_id if dept else None
    status["kiosk"] = True
    status["edge_cache"] = True
    return status


@router.post("/{queue_id}/tickets", status_code=201)
def kiosk_issue(
    queue_id: str,
    body: KioskIssueRequest,
    db: Session = Depends(get_db),
    x_kiosk_token: str | None = Header(default=None, alias="X-Kiosk-Token"),
    idempotency_key: str | None = Depends(get_idempotency_key),
    x_print_provider: str | None = Header(default=None, alias="X-Print-Provider"),
):
    """
    Fluxo TOUCH → SENHA → PRINT.

    A senha é persistida antes da impressão.
    Falha de impressora NÃO duplica nem cancela a senha.
    """
    queue = _require_kiosk(queue_id, x_kiosk_token, db)

    # Idempotência do fluxo completo TOUCH→PRINT (evita reimpressão em duplo toque)
    scope = f"kiosk_issue:{queue_id}"
    if idempotency_key:
        cached = db.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.scope == scope,
                IdempotencyRecord.key == idempotency_key,
            )
        )
        if cached:
            return cached.response_json

    service = QueueService(db)
    ticket_payload = service.create_ticket(
        queue_id,
        ticket_type=body.type.upper(),
        source=body.source.upper() or "KIOSK",
        idempotency_key=f"ticket:{idempotency_key}" if idempotency_key else None,
    )

    ticket = db.get(Ticket, ticket_payload["id"])
    assert ticket is not None

    store_name, dept_name = _context(db, queue)
    people_ahead = int(ticket_payload.get("people_ahead") or 0)
    estimated = int(ticket_payload.get("estimated_wait_seconds") or 0)

    printer = get_printer_provider(x_print_provider)
    print_result = PrintService(db, provider=printer).print_ticket(
        queue=queue,
        ticket=ticket,
        store_name=store_name,
        department_name=dept_name,
        people_ahead=people_ahead,
        estimated_wait_seconds=estimated,
    )

    response = {
        "ticket": ticket_payload,
        "print": print_result,
        "department_name": dept_name,
    }
    if idempotency_key:
        db.add(IdempotencyRecord(scope=scope, key=idempotency_key, response_json=response))
        db.commit()
    # Sprint 11 — espelha emissão no outbox para sync cloud (idempotente)
    try:
        from app.modules.edge.service import EdgeService

        dept = db.get(Department, queue.department_id)
        if dept:
            EdgeService(db).enqueue(
                event_id=idempotency_key or ticket_payload["id"],
                store_id=dept.store_id,
                event_type="TICKET_ISSUED",
                payload={"ticket": ticket_payload, "queue_id": queue_id, "source": "KIOSK"},
                origin_device="kiosk",
            )
    except Exception:
        pass
    publish_queue_event(db, queue_id=queue_id, event="ticket.created", ticket=ticket_payload)
    publish_queue_event(db, queue_id=queue_id, event="queue.updated")
    return response

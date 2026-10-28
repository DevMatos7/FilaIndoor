from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.modules.org.models.entities import Department
from app.modules.queue.models.entities import Queue
from app.modules.realtime.hub import hub


def resolve_store_id(db: Session, queue_id: str) -> str | None:
    queue = db.get(Queue, queue_id)
    if not queue:
        return None
    dept = db.get(Department, queue.department_id)
    return dept.store_id if dept else None


def department_name(db: Session, queue: Queue) -> str:
    if queue.department_display_name:
        return queue.department_display_name
    dept = db.get(Department, queue.department_id)
    return dept.name if dept else queue.name


def publish_queue_event(
    db: Session,
    *,
    queue_id: str,
    event: str,
    ticket: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    store_id = resolve_store_id(db, queue_id)
    if not store_id:
        return
    queue = db.get(Queue, queue_id)
    data: dict[str, Any] = {
        "queue_id": queue_id,
        "department": department_name(db, queue) if queue else "",
    }
    if ticket:
        data["ticket"] = ticket.get("number")
        data["ticket_id"] = ticket.get("id")
        data["ticket_type"] = ticket.get("type")
        data["status"] = ticket.get("status")
    if extra:
        data.update(extra)
    hub.publish(store_id, event, data)

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import QUEUE_ADMIN, QUEUE_MANAGER, QUEUE_OPERATOR, QUEUE_VIEW
from app.db.session import get_db
from app.modules.auth.deps import require_permissions
from app.modules.org.models.entities import User
from app.modules.queue.models.entities import Terminal
from app.modules.queue.services.queue_service import QueueService

router = APIRouter(tags=["terminals"])


class TerminalCreate(BaseModel):
    department_id: str
    name: str
    code: str = Field(min_length=1, max_length=40)


@router.get("/terminals")
def list_terminals(
    department_id: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(QUEUE_VIEW, QUEUE_OPERATOR, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    stmt = select(Terminal).where(Terminal.active.is_(True)).order_by(Terminal.code)
    if department_id:
        stmt = stmt.where(Terminal.department_id == department_id)
    rows = db.scalars(stmt).all()
    return [
        {
            "id": t.id,
            "department_id": t.department_id,
            "name": t.name,
            "code": t.code,
            "active": t.active,
        }
        for t in rows
    ]


@router.post("/terminals", status_code=201)
def create_terminal(
    body: TerminalCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(QUEUE_ADMIN, QUEUE_MANAGER)),
):
    terminal = Terminal(department_id=body.department_id, name=body.name, code=body.code.upper())
    db.add(terminal)
    db.commit()
    db.refresh(terminal)
    return {
        "id": terminal.id,
        "department_id": terminal.department_id,
        "name": terminal.name,
        "code": terminal.code,
        "active": terminal.active,
    }


@router.get("/queues/{queue_id}/operator-panel")
def operator_panel(
    queue_id: str,
    terminal_id: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(QUEUE_OPERATOR, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return QueueService(db).operator_panel(queue_id, terminal_id=terminal_id)

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.permissions import DEVICE_ADMIN, DEVICE_VIEW, QUEUE_ADMIN, QUEUE_MANAGER, QUEUE_VIEW
from app.db.session import get_db
from app.modules.auth.deps import require_permissions
from app.modules.devices.fleet_service import FleetService
from app.modules.devices.service import DeviceService
from app.modules.org.models.entities import User
from app.modules.queue.models.entities import Display, Terminal

router = APIRouter(tags=["devices"])


class DisplayUpdate(BaseModel):
    name: str | None = None
    audio_enabled: bool | None = None
    audio_template: str | None = None
    active: bool | None = None
    playlist_id: str | None = None
    channel_id: str | None = None
    screen_group_id: str | None = None
    store_id: str | None = None


class TerminalUpdate(BaseModel):
    name: str | None = None
    active: bool | None = None


class ChannelAssign(BaseModel):
    channel_id: str | None = None
    store_id: str | None = None


@router.get("/devices/fleet")
def devices_fleet(
    store_id: str = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(DEVICE_VIEW, DEVICE_ADMIN, QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    """UX-10 — overview unificado da frota (sem token bruto)."""
    return FleetService(db).fleet(store_id)


@router.get("/devices/overview")
def devices_overview(
    store_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(DEVICE_VIEW, DEVICE_ADMIN, QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    """Legacy overview — preferir /devices/fleet. Tokens mascarados na listagem."""
    terminals_stmt = select(Terminal).order_by(Terminal.code)
    displays_stmt = select(Display).order_by(Display.code)
    if store_id:
        from app.modules.org.models.entities import Department

        dept_ids = list(
            db.scalars(select(Department.id).where(Department.store_id == store_id)).all()
        )
        displays_stmt = displays_stmt.where(Display.store_id == store_id)
        if dept_ids:
            terminals_stmt = terminals_stmt.where(Terminal.department_id.in_(dept_ids))
        else:
            terminals_stmt = terminals_stmt.where(Terminal.department_id == "__none__")
    terminals = db.scalars(terminals_stmt).all()
    displays = db.scalars(displays_stmt).all()
    svc = DeviceService(db)
    for d in displays:
        svc.ensure_for_display(d)
    managed = svc.list_devices(store_id=store_id)
    by_display = {m["display_id"]: m for m in managed if m.get("display_id")}
    return {
        "terminals": [
            {
                "id": t.id,
                "department_id": t.department_id,
                "name": t.name,
                "code": t.code,
                "active": t.active,
                "kind": "TERMINAL",
            }
            for t in terminals
        ],
        "displays": [
            {
                "id": d.id,
                "store_id": d.store_id,
                "department_id": d.department_id,
                "queue_id": d.queue_id,
                "name": d.name,
                "code": d.code,
                "token_configured": bool(d.token),
                "audio_enabled": d.audio_enabled,
                "audio_template": d.audio_template,
                "active": d.active,
                "playlist_id": d.playlist_id,
                "channel_id": d.channel_id,
                "screen_group_id": d.screen_group_id,
                "kind": "DISPLAY",
                "device": by_display.get(d.id),
            }
            for d in displays
        ],
        "devices": managed,
    }


@router.patch("/displays/{display_id}")
def update_display(
    display_id: str,
    body: DisplayUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(DEVICE_ADMIN, QUEUE_ADMIN, QUEUE_MANAGER)),
):
    data = body.model_dump(exclude_unset=True)
    store_id = data.pop("store_id", None)
    return FleetService(db).update_display_safe(display_id, store_id=store_id, **data)


@router.post("/displays/{display_id}/channel")
def assign_display_channel(
    display_id: str,
    body: ChannelAssign,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(DEVICE_ADMIN, QUEUE_ADMIN, QUEUE_MANAGER)),
):
    return FleetService(db).assign_channel(
        display_id, channel_id=body.channel_id, store_id=body.store_id
    )


@router.patch("/terminals/{terminal_id}")
def update_terminal(
    terminal_id: str,
    body: TerminalUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(DEVICE_ADMIN, QUEUE_ADMIN, QUEUE_MANAGER)),
):
    terminal = db.get(Terminal, terminal_id)
    if not terminal:
        raise NotFoundError("Terminal não encontrado")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(terminal, key, value)
    db.commit()
    db.refresh(terminal)
    return {
        "id": terminal.id,
        "name": terminal.name,
        "code": terminal.code,
        "active": terminal.active,
        "department_id": terminal.department_id,
    }

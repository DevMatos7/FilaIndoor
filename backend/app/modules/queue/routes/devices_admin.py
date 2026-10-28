from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.permissions import DEVICE_ADMIN, DEVICE_VIEW, QUEUE_ADMIN, QUEUE_MANAGER, QUEUE_VIEW
from app.db.session import get_db
from app.modules.auth.deps import require_permissions
from app.modules.org.models.entities import User
from app.modules.devices.service import DeviceService
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


class TerminalUpdate(BaseModel):
    name: str | None = None
    active: bool | None = None


@router.get("/devices/overview")
def devices_overview(
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(DEVICE_VIEW, DEVICE_ADMIN, QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    terminals = db.scalars(select(Terminal).order_by(Terminal.code)).all()
    displays = db.scalars(select(Display).order_by(Display.code)).all()
    svc = DeviceService(db)
    for d in displays:
        svc.ensure_for_display(d)
    managed = svc.list_devices()
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
                "token": d.token,
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
    display = db.get(Display, display_id)
    if not display:
        raise NotFoundError("Display não encontrado")
    fields = body.model_dump(exclude_unset=True)
    for key, value in fields.items():
        setattr(display, key, value)
    db.commit()
    db.refresh(display)
    if fields.keys() & {"playlist_id", "channel_id", "screen_group_id", "audio_enabled", "audio_template"}:
        DeviceService(db).bump_config_version(display_id=display.id)
    return {
        "id": display.id,
        "name": display.name,
        "code": display.code,
        "audio_enabled": display.audio_enabled,
        "audio_template": display.audio_template,
        "active": display.active,
        "token": display.token,
        "queue_id": display.queue_id,
        "playlist_id": display.playlist_id,
        "channel_id": display.channel_id,
        "screen_group_id": display.screen_group_id,
    }


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

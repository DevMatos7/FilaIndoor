from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.session import get_db
from app.modules.org.models.entities import Department
from app.modules.queue.models.entities import Display, Queue
from app.modules.queue.services.queue_service import QueueService
from app.modules.devices.service import DeviceService, device_to_dict
from app.modules.signage.schedule_service import ScheduleService
from app.modules.signage.service import SignageService

router = APIRouter(tags=["player"])


def _display_by_token(db: Session, token: str | None) -> Display:
    if not token:
        raise ForbiddenError("Token do display ausente")
    display = db.scalar(select(Display).where(Display.token == token, Display.active.is_(True)))
    if not display:
        raise ForbiddenError("Display inválido")
    return display


@router.get("/player/config")
def player_config(
    db: Session = Depends(get_db),
    x_display_token: str | None = Header(default=None, alias="X-Display-Token"),
    token: str | None = None,
):
    display = _display_by_token(db, x_display_token or token)
    queue = db.get(Queue, display.queue_id) if display.queue_id else None
    dept = db.get(Department, display.department_id) if display.department_id else None
    status = QueueService(db).queue_status(display.queue_id) if display.queue_id else None
    # Sprint 9: canal/agenda → playlist display → padrão loja → assets
    playlist, schedule_meta = ScheduleService(db).resolve_playlist_for_display(
        store_id=display.store_id,
        channel_id=display.channel_id,
        playlist_id=display.playlist_id,
    )
    if not playlist:
        assets = SignageService(db).list_assets(store_id=display.store_id, active_only=True)
        playlist = [
            {
                "id": a["id"],
                "name": a["name"],
                "type": a["media_type"],
                "url": a["public_url"],
                "mime_type": a["mime_type"],
                "duration_seconds": a["duration_seconds"] or 10,
            }
            for a in assets
            if a["media_type"] in {"IMAGE", "VIDEO", "WEB"}
        ]
        schedule_meta = {**schedule_meta, "source": "assets_fallback"}
    device = DeviceService(db).ensure_for_display(display)
    return {
        "config_version": device.config_version,
        "device": device_to_dict(device),
        "display": {
            "id": display.id,
            "name": display.name,
            "code": display.code,
            "audio_enabled": display.audio_enabled,
            "audio_template": display.audio_template,
            "channel_id": display.channel_id,
            "playlist_id": display.playlist_id,
        },
        "store_id": display.store_id,
        "queue_id": display.queue_id,
        "department": dept.name if dept else (queue.department_display_name if queue else ""),
        "queue": status,
        "channel": {
            "id": display.channel_id,
            "layout": "queue_media_split",
            "schedule": schedule_meta.get("schedule"),
            "source": schedule_meta.get("source"),
            "conflicts": schedule_meta.get("conflicts") or [],
        },
        "playlist": playlist,
        "audio": {
            "enabled": display.audio_enabled,
            "template": display.audio_template,
            "lang": "pt-BR",
        },
        "ws_path": f"/ws/v1/store/{display.store_id}",
    }


@router.get("/displays")
def list_displays(
    store_id: str | None = None,
    db: Session = Depends(get_db),
):
    # Leitura pública mínima para seed/admin links — restringir no futuro
    stmt = select(Display).where(Display.active.is_(True)).order_by(Display.code)
    if store_id:
        stmt = stmt.where(Display.store_id == store_id)
    rows = db.scalars(stmt).all()
    return [
        {
            "id": d.id,
            "store_id": d.store_id,
            "queue_id": d.queue_id,
            "name": d.name,
            "code": d.code,
            "token": d.token,
            "audio_enabled": d.audio_enabled,
        }
        for d in rows
    ]

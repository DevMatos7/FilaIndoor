from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.db.session import get_db
from app.modules.dynamic_content.models import DynamicContent
from app.modules.dynamic_content.snapshot_service import SnapshotService
from app.modules.org.models.entities import Department, Store
from app.modules.queue.models.entities import Display, Queue
from app.modules.queue.services.queue_service import QueueService
from app.modules.devices.service import DeviceService, device_to_dict
from app.modules.signage.layout_service import LayoutService
from app.modules.signage.models import Channel
from app.modules.signage.override_service import ScreenOverrideService
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
    channel = db.get(Channel, display.channel_id) if display.channel_id else None
    legacy_layout = channel.layout if channel else "queue_media_split"
    layout = LayoutService(db).resolve_for_display(
        channel_id=display.channel_id,
        store_id=display.store_id,
    )
    active_overrides = ScreenOverrideService(db).resolve_active_for_display(display)
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
            "layout": legacy_layout,
            "layout_template_id": channel.layout_template_id if channel else None,
            "schedule": schedule_meta.get("schedule"),
            "source": schedule_meta.get("source"),
            "conflicts": schedule_meta.get("conflicts") or [],
        },
        # UX-6B additive — old clients ignore this key
        "layout": layout,
        # UX-6C additive — recovery after reload/reconnect
        "active_overrides": active_overrides,
        "playlist": playlist,
        "audio": {
            "enabled": display.audio_enabled,
            "template": display.audio_template,
            "lang": "pt-BR",
        },
        "ws_path": f"/ws/v1/store/{display.store_id}",
    }


@router.get("/player/dynamic-content/{content_id}")
def player_dynamic_content(
    content_id: str,
    response: Response,
    db: Session = Depends(get_db),
    x_display_token: str | None = Header(default=None, alias="X-Display-Token"),
    token: str | None = None,
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
):
    """Display Player — current PRICE_TABLE snapshot (same-store + active)."""
    display = _display_by_token(db, x_display_token or token)
    content = db.get(DynamicContent, content_id)
    if not content or not content.active:
        raise NotFoundError("conteúdo dinâmico não encontrado")
    if content.store_id != display.store_id:
        raise ForbiddenError("conteúdo de outra loja")

    store = db.get(Store, display.store_id)
    if not store:
        raise NotFoundError("loja não encontrada")

    snaps = SnapshotService(db)
    try:
        snapshot = snaps.ensure_current_snapshot(content, store, allow_stale=False)
    except ValidationError as exc:
        # STALE / FAILED / inactive → player must skip
        raise ForbiddenError(str(exc.message) if hasattr(exc, "message") else str(exc)) from exc

    freshness = (snapshot.get("source") or {}).get("freshness")
    status = snapshot.get("status")
    if freshness in {"STALE", "FAILED"} or status in {"DADOS DESATUALIZADOS", "INATIVA"}:
        raise ForbiddenError("conteúdo não publicável")

    payload = snaps.player_payload(snapshot, content_id=content.id, name=content.name)
    etag = f"\"{payload.get('content_hash') or payload.get('version')}\""
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "private, max-age=0, must-revalidate"

    if if_none_match and if_none_match.strip() == etag:
        return Response(status_code=304)

    return payload


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

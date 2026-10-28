from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError
from app.core.permissions import DEVICE_ADMIN, DEVICE_VIEW, QUEUE_ADMIN, QUEUE_MANAGER, QUEUE_VIEW
from app.db.session import get_db
from app.modules.auth.deps import require_permissions
from app.modules.devices.models import Device
from app.modules.devices.service import DeviceService
from app.modules.org.models.entities import User
from app.modules.queue.models.entities import Display

router = APIRouter(tags=["device-management"])


class PairingRequest(BaseModel):
    device_uuid: str
    device_type: str = "DISPLAY"
    app_version: str | None = None
    name: str | None = None


class EnrollRequest(BaseModel):
    pairing_code: str
    store_id: str
    name: str | None = None
    department_id: str | None = None
    display_id: str | None = None
    audio_enabled: bool | None = None


class HeartbeatRequest(BaseModel):
    online: bool = True
    app_version: str | None = None
    free_storage_mb: int | None = None
    playlist_version: int | None = None
    ip_address: str | None = None
    metadata: dict | None = None
    device_uuid: str | None = None


def _authorize_device(
    db: Session,
    device: Device,
    *,
    device_uuid: str | None,
    display_token: str | None,
) -> None:
    if device_uuid and device.device_uuid == device_uuid:
        return
    if display_token and device.display_id:
        display = db.scalar(
            select(Display).where(Display.id == device.display_id, Display.token == display_token)
        )
        if display:
            return
    raise ForbiddenError("Informe X-Device-UUID ou X-Display-Token válido")


@router.post("/devices/pairing")
def request_pairing(body: PairingRequest, db: Session = Depends(get_db)):
    """Player gera código de pareamento (sem auth)."""
    return DeviceService(db).request_pairing(
        device_uuid=body.device_uuid,
        device_type=body.device_type,
        app_version=body.app_version,
        name=body.name,
    )


@router.post("/devices/enroll")
def enroll_device(
    body: EnrollRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(DEVICE_ADMIN, QUEUE_ADMIN, QUEUE_MANAGER)),
):
    return DeviceService(db).enroll(
        pairing_code=body.pairing_code,
        store_id=body.store_id,
        name=body.name,
        department_id=body.department_id,
        display_id=body.display_id,
        audio_enabled=body.audio_enabled,
    )


@router.get("/devices")
def list_devices(
    store_id: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(DEVICE_VIEW, DEVICE_ADMIN, QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return DeviceService(db).list_devices(store_id=store_id)


@router.get("/devices/{device_id}")
def get_device(
    device_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(DEVICE_VIEW, DEVICE_ADMIN, QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return DeviceService(db).get(device_id)


@router.get("/devices/{device_id}/heartbeats")
def list_heartbeats(
    device_id: str,
    limit: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(DEVICE_VIEW, DEVICE_ADMIN, QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return DeviceService(db).recent_heartbeats(device_id, limit=limit)


@router.post("/devices/{device_id}/heartbeat")
def post_heartbeat(
    device_id: str,
    body: HeartbeatRequest,
    request: Request,
    db: Session = Depends(get_db),
    x_device_uuid: str | None = Header(default=None, alias="X-Device-UUID"),
    x_display_token: str | None = Header(default=None, alias="X-Display-Token"),
):
    svc = DeviceService(db)
    device = db.get(Device, device_id)
    if not device:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("Dispositivo não encontrado")
    _authorize_device(
        db,
        device,
        device_uuid=body.device_uuid or x_device_uuid,
        display_token=x_display_token,
    )
    client_ip = body.ip_address or (request.client.host if request.client else None)
    return svc.heartbeat(
        device_id,
        online=body.online,
        app_version=body.app_version,
        free_storage_mb=body.free_storage_mb,
        playlist_version=body.playlist_version,
        ip_address=client_ip,
        metadata=body.metadata,
    )


@router.post("/devices/{device_id}/enable")
def enable_device(
    device_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(DEVICE_ADMIN, QUEUE_ADMIN, QUEUE_MANAGER)),
):
    return DeviceService(db).enable(device_id)


@router.post("/devices/{device_id}/disable")
def disable_device(
    device_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(DEVICE_ADMIN, QUEUE_ADMIN, QUEUE_MANAGER)),
):
    return DeviceService(db).disable(device_id)

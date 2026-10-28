from __future__ import annotations

import random
import secrets
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.devices.models import Device, DeviceHeartbeat
from app.modules.org.models.entities import Store
from app.modules.queue.models.entities import Display, utcnow

ONLINE_SECONDS = 90
DEGRADED_SECONDS = 300
PAIRING_TTL_SECONDS = 600
DEVICE_TYPES = {"KIOSK", "PRINTER", "DISPLAY", "BUTTON", "EDGE"}


def _compute_status(device: Device, now: datetime | None = None) -> str:
    if device.status == "DISABLED":
        return "DISABLED"
    if not device.store_id:
        return "OFFLINE"
    now = now or utcnow()
    if not device.last_seen_at:
        return "OFFLINE"
    age = (now - device.last_seen_at).total_seconds()
    if age <= ONLINE_SECONDS:
        return "ONLINE"
    if age <= DEGRADED_SECONDS:
        return "DEGRADED"
    return "OFFLINE"


def device_to_dict(device: Device, *, include_secrets: bool = False) -> dict[str, Any]:
    computed = _compute_status(device)
    data: dict[str, Any] = {
        "id": device.id,
        "store_id": device.store_id,
        "department_id": device.department_id,
        "display_id": device.display_id,
        "device_type": device.device_type,
        "name": device.name,
        "device_uuid": device.device_uuid,
        "status": computed,
        "status_stored": device.status,
        "audio_enabled": device.audio_enabled,
        "last_seen_at": device.last_seen_at.isoformat() + "Z" if device.last_seen_at else None,
        "app_version": device.app_version,
        "config_version": device.config_version,
        "ip_address": device.ip_address,
        "enrolled": bool(device.store_id and device.enrolled_at),
        "enrolled_at": device.enrolled_at.isoformat() + "Z" if device.enrolled_at else None,
        "metadata": device.metadata_json or {},
        "created_at": device.created_at.isoformat() + "Z" if device.created_at else None,
    }
    if include_secrets and device.pairing_code and device.pairing_expires_at and device.pairing_expires_at > utcnow():
        data["pairing_code"] = device.pairing_code
        data["pairing_expires_at"] = device.pairing_expires_at.isoformat() + "Z"
    return data


class DeviceService:
    def __init__(self, db: Session):
        self.db = db

    def list_devices(self, store_id: str | None = None) -> list[dict[str, Any]]:
        stmt = select(Device).order_by(Device.name)
        if store_id:
            stmt = stmt.where(Device.store_id == store_id)
        rows = self.db.scalars(stmt).all()
        return [device_to_dict(d) for d in rows]

    def get(self, device_id: str) -> dict[str, Any]:
        return device_to_dict(self._device(device_id))

    def request_pairing(
        self,
        *,
        device_uuid: str,
        device_type: str = "DISPLAY",
        app_version: str | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        device_uuid = (device_uuid or "").strip()
        if not device_uuid:
            raise ValidationError("device_uuid obrigatório")
        device_type = (device_type or "DISPLAY").upper()
        if device_type not in DEVICE_TYPES:
            raise ValidationError(f"device_type inválido: {device_type}")

        device = self.db.scalar(select(Device).where(Device.device_uuid == device_uuid))
        if device and device.store_id and device.status != "DISABLED":
            # já enrolled — devolve estado atual sem novo código
            return {
                **device_to_dict(device),
                "already_enrolled": True,
                "pairing_code": None,
            }

        code = self._unique_pairing_code()
        expires = utcnow() + timedelta(seconds=PAIRING_TTL_SECONDS)
        if not device:
            device = Device(
                device_uuid=device_uuid,
                device_type=device_type,
                name=(name or f"{device_type} {code}").strip(),
                status="OFFLINE",
            )
            self.db.add(device)
        device.pairing_code = code
        device.pairing_expires_at = expires
        device.device_type = device_type
        if app_version:
            device.app_version = app_version
        if name:
            device.name = name.strip()
        self.db.commit()
        self.db.refresh(device)
        return {
            **device_to_dict(device, include_secrets=True),
            "already_enrolled": False,
            "pairing_code": code,
            "expires_in": PAIRING_TTL_SECONDS,
        }

    def enroll(
        self,
        *,
        pairing_code: str,
        store_id: str,
        name: str | None = None,
        department_id: str | None = None,
        display_id: str | None = None,
        audio_enabled: bool | None = None,
    ) -> dict[str, Any]:
        code = (pairing_code or "").strip()
        if not code:
            raise ValidationError("pairing_code obrigatório")
        store = self.db.get(Store, store_id)
        if not store:
            raise NotFoundError("Loja não encontrada")

        device = self.db.scalar(select(Device).where(Device.pairing_code == code))
        if not device:
            raise NotFoundError("Código de pareamento inválido")
        if not device.pairing_expires_at or device.pairing_expires_at < utcnow():
            raise ValidationError("Código de pareamento expirado")

        if display_id:
            display = self.db.get(Display, display_id)
            if not display:
                raise NotFoundError("Display não encontrado")
            if display.store_id != store_id:
                raise ValidationError("Display não pertence à loja")
            other = self.db.scalar(select(Device).where(Device.display_id == display_id, Device.id != device.id))
            if other:
                raise ConflictError("Display já vinculado a outro dispositivo")
            device.display_id = display_id
            device.audio_enabled = display.audio_enabled if audio_enabled is None else audio_enabled
            if not name:
                name = display.name

        device.store_id = store_id
        device.department_id = department_id
        if name:
            device.name = name.strip()
        if audio_enabled is not None:
            device.audio_enabled = audio_enabled
        device.pairing_code = None
        device.pairing_expires_at = None
        device.enrolled_at = utcnow()
        if device.status == "DISABLED":
            device.status = "OFFLINE"
        self.db.commit()
        self.db.refresh(device)
        return device_to_dict(device)

    def heartbeat(
        self,
        device_id: str,
        *,
        device_uuid: str | None = None,
        online: bool = True,
        app_version: str | None = None,
        free_storage_mb: int | None = None,
        playlist_version: int | None = None,
        ip_address: str | None = None,
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        device = self._device(device_id)
        if device_uuid and device.device_uuid != device_uuid:
            raise ValidationError("device_uuid não confere")
        if device.status == "DISABLED":
            raise ValidationError("Dispositivo desabilitado")
        if not device.store_id:
            raise ValidationError("Dispositivo ainda não enrolled")

        now = utcnow()
        device.last_seen_at = now
        device.status = "ONLINE" if online else "DEGRADED"
        if app_version:
            device.app_version = app_version
        if ip_address:
            device.ip_address = ip_address
        meta = dict(device.metadata_json or {})
        if free_storage_mb is not None:
            meta["free_storage_mb"] = free_storage_mb
        if playlist_version is not None:
            meta["playlist_version"] = playlist_version
        if metadata:
            meta.update(metadata)
        device.metadata_json = meta

        hb = DeviceHeartbeat(
            device_id=device.id,
            timestamp=now,
            ip=ip_address,
            app_version=app_version,
            free_storage_mb=free_storage_mb,
            playlist_version=playlist_version,
            metadata_json=metadata,
        )
        self.db.add(hb)
        self.db.commit()
        self.db.refresh(device)
        return {
            **device_to_dict(device),
            "heartbeat_id": hb.id,
            "config_version": device.config_version,
        }

    def enable(self, device_id: str) -> dict[str, Any]:
        device = self._device(device_id)
        device.status = "OFFLINE"
        self.db.commit()
        self.db.refresh(device)
        return device_to_dict(device)

    def disable(self, device_id: str) -> dict[str, Any]:
        device = self._device(device_id)
        device.status = "DISABLED"
        self.db.commit()
        self.db.refresh(device)
        return device_to_dict(device)

    def bump_config_version(self, *, display_id: str | None = None, device_id: str | None = None) -> int | None:
        device = None
        if device_id:
            device = self.db.get(Device, device_id)
        elif display_id:
            device = self.db.scalar(select(Device).where(Device.display_id == display_id))
        if not device:
            return None
        device.config_version = int(device.config_version or 1) + 1
        self.db.commit()
        return device.config_version

    def ensure_for_display(self, display: Display) -> Device:
        existing = self.db.scalar(select(Device).where(Device.display_id == display.id))
        if existing:
            return existing
        # device_uuid estável derivado do display
        uuid_key = f"display:{display.id}"
        by_uuid = self.db.scalar(select(Device).where(Device.device_uuid == uuid_key))
        if by_uuid:
            by_uuid.display_id = display.id
            by_uuid.store_id = display.store_id
            by_uuid.department_id = display.department_id
            if not by_uuid.enrolled_at:
                by_uuid.enrolled_at = utcnow()
            self.db.commit()
            self.db.refresh(by_uuid)
            return by_uuid
        device = Device(
            store_id=display.store_id,
            department_id=display.department_id,
            display_id=display.id,
            device_type="DISPLAY",
            name=display.name,
            device_uuid=uuid_key,
            status="OFFLINE",
            audio_enabled=display.audio_enabled,
            enrolled_at=utcnow(),
            config_version=1,
        )
        self.db.add(device)
        self.db.commit()
        self.db.refresh(device)
        return device

    def recent_heartbeats(self, device_id: str, limit: int = 20) -> list[dict[str, Any]]:
        self._device(device_id)
        rows = self.db.scalars(
            select(DeviceHeartbeat)
            .where(DeviceHeartbeat.device_id == device_id)
            .order_by(DeviceHeartbeat.timestamp.desc())
            .limit(min(limit, 100))
        ).all()
        return [
            {
                "id": h.id,
                "device_id": h.device_id,
                "timestamp": h.timestamp.isoformat() + "Z",
                "ip": h.ip,
                "app_version": h.app_version,
                "free_storage_mb": h.free_storage_mb,
                "playlist_version": h.playlist_version,
                "metadata": h.metadata_json or {},
            }
            for h in rows
        ]

    def _device(self, device_id: str) -> Device:
        device = self.db.get(Device, device_id)
        if not device:
            raise NotFoundError("Dispositivo não encontrado")
        return device

    def _unique_pairing_code(self) -> str:
        for _ in range(30):
            code = f"{random.randint(0, 999999):06d}"
            exists = self.db.scalar(select(Device.id).where(Device.pairing_code == code))
            if not exists:
                return code
        return secrets.token_hex(3)

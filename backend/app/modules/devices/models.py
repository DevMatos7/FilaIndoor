from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.modules.queue.models.entities import new_id, utcnow


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        Index("ix_devices_store_status", "store_id", "status"),
        Index("ix_devices_pairing_code", "pairing_code"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    store_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("stores.id", ondelete="SET NULL"), nullable=True, index=True
    )
    department_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    display_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("displays.id", ondelete="SET NULL"), nullable=True, unique=True, index=True
    )

    device_type: Mapped[str] = mapped_column(String(20), nullable=False, default="DISPLAY")
    name: Mapped[str] = mapped_column(String(180), nullable=False, default="Novo dispositivo")
    device_uuid: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OFFLINE")
    audio_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    config_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    pairing_code: Mapped[str | None] = mapped_column(String(12), nullable=True)
    pairing_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    enrolled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class DeviceHeartbeat(Base):
    __tablename__ = "device_heartbeats"
    __table_args__ = (Index("ix_device_heartbeats_device_ts", "device_id", "timestamp"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    device_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    free_storage_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    playlist_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

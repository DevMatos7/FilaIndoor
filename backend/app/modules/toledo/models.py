from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.modules.queue.models.entities import new_id, utcnow


class ToledoDiscovery(Base):
    """Checklist de discovery — não armazena chave de integração em claro se marcado secret."""

    __tablename__ = "toledo_discoveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    store_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    environment_name: Mapped[str] = mapped_column(String(120), nullable=False, default="default")
    mgv_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    mit_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    mit_cloud: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    mit_cloud_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    license_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    stores_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    players_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    api_base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    auth_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    integration_key_configured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    network_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    docs_compared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confirmed_capabilities: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    mode_intent: Mapped[str] = mapped_column(String(40), nullable=False, default="NATIVE")
    updated_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

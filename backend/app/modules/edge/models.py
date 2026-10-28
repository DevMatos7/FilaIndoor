from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import JSON

from app.db.session import Base
from app.modules.queue.models.entities import new_id, utcnow


class EdgeOutboxEvent(Base):
    """Eventos gerados no edge para sync (idempotente por event_id)."""

    __tablename__ = "edge_outbox_events"
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_edge_outbox_event_id"),
        Index("ix_edge_outbox_store_status", "store_id", "sync_status"),
        Index("ix_edge_outbox_occurred", "occurred_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    store_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True
    )
    origin_device: Mapped[str | None] = mapped_column(String(120), nullable=True)
    origin_edge: Mapped[str] = mapped_column(String(80), nullable=False, default="store-edge")
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    sync_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

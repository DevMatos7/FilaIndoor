from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.modules.queue.models.entities import new_id, utcnow


class VirtualTicket(Base):
    """Senha retirada remotamente (REAL+) com tracking público."""

    __tablename__ = "virtual_tickets"
    __table_args__ = (
        UniqueConstraint("tracking_token", name="uq_virtual_tickets_tracking"),
        Index("ix_virtual_tickets_ticket_id", "ticket_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    ticket_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    queue_id: Mapped[str] = mapped_column(String(36), ForeignKey("queues.id", ondelete="CASCADE"), nullable=False)
    tracking_token: Mapped[str] = mapped_column(String(64), nullable=False)
    customer_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # WAITING_REMOTE | APPROACHING | CHECKED_IN | CALLED | DONE | CANCELLED
    presence_status: Mapped[str] = mapped_column(String(30), nullable=False, default="WAITING_REMOTE")
    notify_when_ahead: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    push_endpoint: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_notified_ahead: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class VirtualNotification(Base):
    __tablename__ = "virtual_notifications"
    __table_args__ = (Index("ix_virtual_notifications_virtual", "virtual_ticket_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    virtual_ticket_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("virtual_tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(40), nullable=False, default="IN_APP")  # IN_APP | PUSH_STUB
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    delivered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

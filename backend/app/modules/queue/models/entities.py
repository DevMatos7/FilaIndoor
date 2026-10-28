import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def new_id() -> str:
    return str(uuid.uuid4())


class Terminal(Base):
    __tablename__ = "terminals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    department_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("department_id", "code", name="uq_terminal_dept_code"),)


class Display(Base):
    """Player de TV (Sprint 4)."""

    __tablename__ = "displays"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    store_id: Mapped[str] = mapped_column(String(36), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    queue_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("queues.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    token: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    audio_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    audio_template: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="Senha {number}. Favor dirigir-se ao {department}.",
    )
    playlist_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    channel_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    screen_group_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("store_id", "code", name="uq_display_store_code"),)


class Queue(Base):
    __tablename__ = "queues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    department_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")

    normal_prefix: Mapped[str] = mapped_column(String(8), nullable=False, default="A")
    priority_prefix: Mapped[str] = mapped_column(String(8), nullable=False, default="P")
    digits: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    initial_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    final_number: Mapped[int] = mapped_column(Integer, nullable=False, default=999)
    reset_policy: Mapped[str] = mapped_column(String(20), nullable=False, default="DAILY")
    priority_strategy: Mapped[str] = mapped_column(String(20), nullable=False, default="WEIGHTED")

    # Totem / kiosk (Sprint 2)
    kiosk_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    kiosk_token: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    department_display_name: Mapped[str | None] = mapped_column(String(180), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    department = relationship("Department", back_populates="queues")
    priority_rule: Mapped["QueuePriorityRule | None"] = relationship(
        back_populates="queue", uselist=False, cascade="all, delete-orphan"
    )
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="queue", cascade="all, delete-orphan")
    sequences: Mapped[list["QueueSequence"]] = relationship(back_populates="queue", cascade="all, delete-orphan")
    print_jobs: Mapped[list["PrintJob"]] = relationship(back_populates="queue", cascade="all, delete-orphan")


class QueuePriorityRule(Base):
    __tablename__ = "queue_priority_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    queue_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("queues.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    normal_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    priority_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    priority_max_wait_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=600)
    normal_max_wait_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    queue: Mapped[Queue] = relationship(back_populates="priority_rule")


class QueueSequence(Base):
    """Contador protegido por linha (SELECT FOR UPDATE) — nunca MAX(number)+1."""

    __tablename__ = "queue_sequences"
    __table_args__ = (UniqueConstraint("queue_id", "ticket_type", "period_key", name="uq_queue_seq"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    queue_id: Mapped[str] = mapped_column(String(36), ForeignKey("queues.id", ondelete="CASCADE"), nullable=False)
    ticket_type: Mapped[str] = mapped_column(String(20), nullable=False)
    period_key: Mapped[str] = mapped_column(String(32), nullable=False, default="default")
    current_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    queue: Mapped[Queue] = relationship(back_populates="sequences")


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        Index("ix_tickets_queue_status_issued", "queue_id", "status", "issued_at"),
        Index("ix_tickets_queue_type_status_issued", "queue_id", "ticket_type", "status", "issued_at"),
        UniqueConstraint("queue_id", "display_number", "period_key", name="uq_ticket_display"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    queue_id: Mapped[str] = mapped_column(String(36), ForeignKey("queues.id", ondelete="CASCADE"), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    display_number: Mapped[str] = mapped_column(String(32), nullable=False)
    period_key: Mapped[str] = mapped_column(String(32), nullable=False, default="default")
    ticket_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="WAITING")

    issued_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    called_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    service_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    no_show_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    terminal_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    operator_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="KIOSK")
    source_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    queue: Mapped[Queue] = relationship(back_populates="tickets")
    events: Mapped[list["TicketEvent"]] = relationship(back_populates="ticket", cascade="all, delete-orphan")


class TicketEvent(Base):
    __tablename__ = "ticket_events"
    __table_args__ = (Index("ix_ticket_events_ticket_at", "ticket_id", "event_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    ticket_id: Mapped[str] = mapped_column(String(36), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    event_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    operator_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    terminal_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    ticket: Mapped[Ticket] = relationship(back_populates="events")


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (UniqueConstraint("scope", "key", name="uq_idempotency_scope_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    scope: Mapped[str] = mapped_column(String(120), nullable=False)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    response_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class PrintJob(Base):
    __tablename__ = "print_jobs"
    __table_args__ = (Index("ix_print_jobs_ticket", "ticket_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    queue_id: Mapped[str] = mapped_column(String(36), ForeignKey("queues.id", ondelete="CASCADE"), nullable=False)
    ticket_id: Mapped[str] = mapped_column(String(36), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    queue: Mapped[Queue] = relationship(back_populates="print_jobs")
    ticket: Mapped["Ticket"] = relationship()

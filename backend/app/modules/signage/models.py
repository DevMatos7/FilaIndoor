from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.modules.queue.models.entities import new_id, utcnow


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    store_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    media_type: Mapped[str] = mapped_column(String(20), nullable=False)  # IMAGE | VIDEO | WEB
    mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    public_url: Mapped[str] = mapped_column(String(500), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class Playlist(Base):
    __tablename__ = "playlists"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    store_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    items: Mapped[list["PlaylistItem"]] = relationship(
        back_populates="playlist", cascade="all, delete-orphan", order_by="PlaylistItem.position"
    )


class PlaylistItem(Base):
    __tablename__ = "playlist_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    playlist_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    playlist: Mapped[Playlist] = relationship(back_populates="items")
    asset: Mapped[MediaAsset] = relationship()


class LayoutTemplate(Base):
    """Template data-driven de composição da TV (UX-6B)."""

    __tablename__ = "layout_templates"
    __table_args__ = (UniqueConstraint("store_id", "slug", name="uq_layout_templates_store_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    store_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("stores.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    orientation: Mapped[str] = mapped_column(String(20), nullable=False, default="LANDSCAPE")
    aspect_ratio: Mapped[str] = mapped_column(String(20), nullable=False, default="16:9")
    background: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    zones: Mapped[list["LayoutZone"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="LayoutZone.z_index",
    )


class LayoutZone(Base):
    """Zona geométrica percentual (0–100) de um layout template."""

    __tablename__ = "layout_zones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    layout_template_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("layout_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    zone_type: Mapped[str] = mapped_column(String(40), nullable=False)  # MEDIA|QUEUE|TEXT|CLOCK|TICKER
    x: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    y: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    width: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=100)
    height: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=100)
    z_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    template: Mapped[LayoutTemplate] = relationship(back_populates="zones")


class Channel(Base):
    """Canal de conteúdo indoor (Sprint 9)."""

    __tablename__ = "channels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    store_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    # Legacy string layout — preservado (UX-6B). Remoção só após migração total de canais.
    layout: Mapped[str] = mapped_column(String(60), nullable=False, default="queue_media_split")
    layout_template_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("layout_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    default_playlist_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    schedules: Mapped[list["Schedule"]] = relationship(
        back_populates="channel", cascade="all, delete-orphan"
    )
    groups: Mapped[list["ScreenGroup"]] = relationship(
        back_populates="channel", cascade="all, delete-orphan"
    )
    layout_template: Mapped[LayoutTemplate | None] = relationship()


class ScreenGroup(Base):
    """Grupo de telas ligado a um canal."""

    __tablename__ = "screen_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    store_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    channel: Mapped[Channel] = relationship(back_populates="groups")


class Schedule(Base):
    """Agenda de playlist em um canal (dias/horários + prioridade)."""

    __tablename__ = "schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    channel_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    playlist_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False, default="Agenda")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False, default=time(0, 0))
    end_time: Mapped[time] = mapped_column(Time, nullable=False, default=time(23, 59))
    # ISO weekday CSV: 0=seg ... 6=dom (datetime.weekday())
    days_of_week: Mapped[str] = mapped_column(String(32), nullable=False, default="0,1,2,3,4,5,6")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="NORMAL")  # NORMAL|HIGH|EMERGENCY
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    channel: Mapped[Channel] = relationship(back_populates="schedules")
    playlist: Mapped[Playlist] = relationship()

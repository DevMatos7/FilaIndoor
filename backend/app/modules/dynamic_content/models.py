from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _uuid() -> str:
    return str(uuid4())


JsonType = JSON().with_variant(JSONB(), "postgresql")


class DynamicContentTemplate(Base):
    __tablename__ = "dynamic_content_templates"
    __table_args__ = (UniqueConstraint("store_id", "slug", name="uq_dynamic_content_templates_store_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    store_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("stores.id", ondelete="CASCADE"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    content_type: Mapped[str] = mapped_column(String(40), nullable=False, default="PRICE_TABLE")
    orientation: Mapped[str] = mapped_column(String(20), nullable=False, default="landscape")
    aspect_ratio: Mapped[str] = mapped_column(String(20), nullable=False, default="16:9")
    config: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class DynamicContent(Base):
    __tablename__ = "dynamic_contents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    store_id: Mapped[str] = mapped_column(String(36), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_type: Mapped[str] = mapped_column(String(40), nullable=False, default="PRICE_TABLE")
    selection_mode: Mapped[str] = mapped_column(String(20), nullable=False)  # MANUAL|AUTOMATIC|HYBRID
    template_id: Mapped[str] = mapped_column(String(36), ForeignKey("dynamic_content_templates.id"), nullable=False)
    config: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class DynamicContentRule(Base):
    __tablename__ = "dynamic_content_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    dynamic_content_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("dynamic_contents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    group_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    subgroup_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    promotion_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    available_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    limit_items: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sort_mode: Mapped[str] = mapped_column(String(40), nullable=False, default="NAME_ASC")
    config: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class DynamicContentProduct(Base):
    __tablename__ = "dynamic_content_products"
    __table_args__ = (
        UniqueConstraint("dynamic_content_id", "product_id", name="uq_dynamic_content_product"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    dynamic_content_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("dynamic_contents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("retail_products.id", ondelete="CASCADE"), nullable=False)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    excluded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class DynamicRenderSnapshot(Base):
    __tablename__ = "dynamic_render_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    dynamic_content_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("dynamic_contents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    store_id: Mapped[str] = mapped_column(String(36), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    data_version: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_freshness: Mapped[str] = mapped_column(String(20), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    publishable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    warnings: Mapped[list] = mapped_column(JsonType, nullable=False, default=list)

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.modules.queue.models.entities import new_id, utcnow


class Integration(Base):
    __tablename__ = "integrations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    store_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("stores.id", ondelete="SET NULL"), nullable=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="mock")
    name: Mapped[str] = mapped_column(String(120), nullable=False, default="ERP")
    external_store_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    config_json: Mapped[dict | None] = mapped_column("config", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class IntegrationSyncRun(Base):
    __tablename__ = "integration_sync_runs"
    __table_args__ = (Index("ix_integration_sync_runs_started", "started_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    integration_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    store_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    sync_type: Mapped[str] = mapped_column(String(40), nullable=False, default="FULL")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="RUNNING")
    products_upserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    snapshots_upserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ErpProduct(Base):
    __tablename__ = "erp_products"
    __table_args__ = (
        UniqueConstraint("provider", "external_product_id", name="uq_erp_product_provider_ext"),
        Index("ix_erp_products_sku", "sku"),
        Index("ix_erp_products_ean", "ean"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="mock")
    external_product_id: Mapped[str] = mapped_column(String(80), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ean: Mapped[str | None] = mapped_column(String(32), nullable=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    section_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    group_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    subgroup_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class ErpProductStoreSnapshot(Base):
    __tablename__ = "erp_product_store_snapshots"
    __table_args__ = (
        UniqueConstraint("product_id", "store_id", name="uq_erp_snapshot_product_store"),
        Index("ix_erp_snapshots_store", "store_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("erp_products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    store_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    regular_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    promo_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    promo_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    promo_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    stock_qty: Mapped[float | None] = mapped_column(Float, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class ProductOfferTemplate(Base):
    """Campanha dinâmica — aponta para product_external_id; render usa snapshot local."""

    __tablename__ = "product_offer_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    store_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    product_external_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    template_key: Mapped[str] = mapped_column(String(60), nullable=False, default="oferta_acougue")
    only_in_stock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    min_stock_qty: Mapped[float] = mapped_column(Float, nullable=False, default=0.01)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

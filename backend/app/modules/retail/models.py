from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _uuid() -> str:
    return str(uuid4())


class RetailStoreSource(Base):
    __tablename__ = "retail_store_sources"
    __table_args__ = (
        UniqueConstraint("store_id", "source_system", name="uq_retail_store_source_store_sys"),
        UniqueConstraint("source_system", "company_code", name="uq_retail_store_source_sys_company"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    store_id: Mapped[str] = mapped_column(String(36), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    source_system: Mapped[str] = mapped_column(String(40), nullable=False, default="CISS")
    company_code: Mapped[str] = mapped_column(String(40), nullable=False)
    location_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class RetailProduct(Base):
    __tablename__ = "retail_products"
    __table_args__ = (UniqueConstraint("source_system", "source_product_id", name="uq_retail_product_source"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source_system: Mapped[str] = mapped_column(String(40), nullable=False, default="CISS")
    source_product_id: Mapped[str] = mapped_column(String(80), nullable=False)
    gtin: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    commercial_description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    section_code: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    section_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    group_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    group_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    subgroup_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    subgroup_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(120), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class RetailStoreProduct(Base):
    __tablename__ = "retail_store_products"
    __table_args__ = (UniqueConstraint("store_id", "product_id", name="uq_retail_store_product"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    store_id: Mapped[str] = mapped_column(String(36), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("retail_products.id", ondelete="CASCADE"), nullable=False)
    source_company_code: Mapped[str] = mapped_column(String(40), nullable=False)
    sellable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    current_stock_qty: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class RetailPrice(Base):
    __tablename__ = "retail_prices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    store_id: Mapped[str] = mapped_column(String(36), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("retail_products.id", ondelete="CASCADE"), nullable=False)
    price_kind: Mapped[str] = mapped_column(String(20), nullable=False)  # REGULAR | PROMOTION | QUANTITY
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    min_qty: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_qty: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    condition_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class RetailPromotion(Base):
    __tablename__ = "retail_promotions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    store_id: Mapped[str] = mapped_column(String(36), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("retail_products.id", ondelete="CASCADE"), nullable=False)
    source_promotion_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    promotion_type: Mapped[str] = mapped_column(String(40), nullable=False, default="NORMAL")
    promo_amount: Mapped[float] = mapped_column(Float, nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    condition_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class RetailSyncWatermark(Base):
    __tablename__ = "retail_sync_watermarks"
    __table_args__ = (UniqueConstraint("source_system", "entity", "store_id", name="uq_retail_sync_watermark"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source_system: Mapped[str] = mapped_column(String(40), nullable=False, default="CISS")
    entity: Mapped[str] = mapped_column(String(40), nullable=False)
    store_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("stores.id", ondelete="CASCADE"), nullable=True)
    watermark_value: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class ProductMediaLink(Base):
    """Associação Product → MediaAsset (sem duplicar arquivo)."""

    __tablename__ = "product_media_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("retail_products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    store_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("stores.id", ondelete="CASCADE"), nullable=True, index=True
    )
    media_asset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("media_assets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    purpose: Mapped[str] = mapped_column(String(20), nullable=False, default="PRIMARY")  # PRIMARY|SECONDARY|BACKGROUND
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="MANUAL")  # MANUAL|CISS|SUPPLIER
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class RetailSyncRun(Base):
    __tablename__ = "retail_sync_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source_system: Mapped[str] = mapped_column(String(40), nullable=False, default="CISS")
    entity: Mapped[str] = mapped_column(String(40), nullable=False)
    store_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("stores.id", ondelete="SET NULL"), nullable=True, index=True)
    trigger: Mapped[str] = mapped_column(String(20), nullable=False, default="MANUAL")  # MANUAL|SCHEDULED|CLI
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="RUNNING")
    records_read: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    watermark_before: Mapped[str | None] = mapped_column(String(120), nullable=True)
    watermark_after: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class RetailPriceChain(Base):
    """CISS PRODUTO_CADEIA_PRECO — grupo comercial (não é SKU)."""

    __tablename__ = "retail_price_chains"
    __table_args__ = (UniqueConstraint("source_system", "source_chain_id", name="uq_retail_price_chain"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source_system: Mapped[str] = mapped_column(String(40), nullable=False, default="CISS")
    source_chain_id: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(String(120), nullable=False)
    gondola_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class RetailProductPriceChain(Base):
    __tablename__ = "retail_product_price_chains"
    __table_args__ = (
        UniqueConstraint("product_id", "price_chain_id", name="uq_retail_product_price_chain"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("retail_products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    price_chain_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("retail_price_chains.id", ondelete="CASCADE"), nullable=False, index=True
    )
    synced_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class RetailOfferCampaign(Base):
    """CISS PROMOCAO_GESTAO — campanha/oferta gerenciada (≠ RetailPromotion de política)."""

    __tablename__ = "retail_offer_campaigns"
    __table_args__ = (
        UniqueConstraint("store_id", "source_system", "source_offer_id", name="uq_retail_offer_campaign"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    store_id: Mapped[str] = mapped_column(String(36), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    source_system: Mapped[str] = mapped_column(String(40), nullable=False, default="CISS")
    source_offer_id: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class RetailOfferItem(Base):
    __tablename__ = "retail_offer_items"
    __table_args__ = (
        UniqueConstraint("campaign_id", "product_id", name="uq_retail_offer_item"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    campaign_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("retail_offer_campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("retail_products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    price_chain_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("retail_price_chains.id", ondelete="SET NULL"), nullable=True
    )
    regular_price: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    offer_price: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    raw_offer_price: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    calculation_type: Mapped[str] = mapped_column(String(30), nullable=False, default="DIRECT")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

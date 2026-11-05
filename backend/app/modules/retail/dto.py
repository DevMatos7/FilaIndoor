from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class CanonicalProduct:
    source_product_id: str
    description: str
    commercial_description: str | None = None
    gtin: str | None = None
    unit: str | None = "UN"
    section_code: str | None = None
    section_name: str | None = None
    group_code: str | None = None
    group_name: str | None = None
    subgroup_code: str | None = None
    subgroup_name: str | None = None
    brand: str | None = None
    active: bool = True
    source_updated_at: datetime | None = None


@dataclass
class CanonicalStoreProduct:
    source_product_id: str
    company_code: str
    sellable: bool = True
    available: bool = True
    stock_qty: float | None = None
    source_updated_at: datetime | None = None


@dataclass
class CanonicalPrice:
    source_product_id: str
    price_kind: str  # REGULAR | PROMOTION | QUANTITY
    amount: float
    min_qty: float | None = None
    max_qty: float | None = None
    unit: str | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    source_ref: str | None = None
    condition_text: str | None = None
    active: bool = True
    source_updated_at: datetime | None = None


@dataclass
class CanonicalPromotion:
    source_product_id: str
    promo_amount: float
    source_promotion_id: str | None = None
    promotion_type: str = "NORMAL"
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    condition_text: str | None = None
    active: bool = True
    source_updated_at: datetime | None = None

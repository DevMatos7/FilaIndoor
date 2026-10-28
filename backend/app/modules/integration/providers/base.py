from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass
class ERPStore:
    external_id: str
    name: str
    company_external_id: str | None = None
    stock_location_id: str | None = None
    raw: dict[str, Any] | None = None


@dataclass
class ERPProduct:
    external_product_id: str
    sku: str | None
    ean: str | None
    description: str
    unit: str | None = "UN"
    section_code: str | None = None
    group_code: str | None = None
    subgroup_code: str | None = None
    raw: dict[str, Any] | None = None


@dataclass
class ERPPrice:
    external_product_id: str
    regular_price: float | None
    promo_price: float | None = None
    promo_start: datetime | None = None
    promo_end: datetime | None = None
    currency: str = "BRL"


@dataclass
class ERPStock:
    external_product_id: str
    stock_qty: float
    stock_location_id: str | None = None


@dataclass
class ERPPromotion:
    external_product_id: str
    promo_price: float
    promo_start: datetime | None = None
    promo_end: datetime | None = None
    label: str | None = None


def dataclass_to_dict(obj: Any) -> dict[str, Any]:
    data = asdict(obj)
    for key, value in list(data.items()):
        if isinstance(value, datetime):
            data[key] = value.isoformat() + "Z"
    return data


class ERPProvider(ABC):
    """Interface de leitura do ERP. Nunca gravar no CISS a partir desta camada."""

    name: str = "base"

    @abstractmethod
    def get_store(self, external_store_id: str) -> ERPStore | None: ...

    @abstractmethod
    def get_product(self, external_product_id: str) -> ERPProduct | None: ...

    @abstractmethod
    def get_products(self, *, since: datetime | None = None, limit: int = 500) -> list[ERPProduct]: ...

    @abstractmethod
    def get_price(self, external_product_id: str, *, store_external_id: str | None = None) -> ERPPrice | None: ...

    @abstractmethod
    def get_stock(self, external_product_id: str, *, store_external_id: str | None = None) -> ERPStock | None: ...

    @abstractmethod
    def get_promotions(self, *, store_external_id: str | None = None) -> list[ERPPromotion]: ...

    def capabilities(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "read_only": True,
            "writes_forbidden": True,
            "supports": ["store", "product", "price", "stock", "promotions"],
        }

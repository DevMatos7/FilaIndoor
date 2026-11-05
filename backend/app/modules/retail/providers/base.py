from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from app.modules.retail.dto import (
    CanonicalPrice,
    CanonicalProduct,
    CanonicalPromotion,
    CanonicalStoreProduct,
)


class RetailDataProvider(ABC):
    """Fonte de dados retail — somente leitura."""

    name: str = "base"

    @abstractmethod
    def fetch_products(self, *, since: datetime | None = None, limit: int = 500) -> list[CanonicalProduct]: ...

    @abstractmethod
    def fetch_store_products(
        self, *, company_code: str, since: datetime | None = None, limit: int = 500
    ) -> list[CanonicalStoreProduct]: ...

    @abstractmethod
    def fetch_prices(
        self,
        *,
        company_code: str,
        since: datetime | None = None,
        limit: int = 500,
        store_timezone: str | None = None,
    ) -> list[CanonicalPrice]: ...

    @abstractmethod
    def fetch_promotions(
        self,
        *,
        company_code: str,
        since: datetime | None = None,
        limit: int = 500,
        store_timezone: str | None = None,
    ) -> list[CanonicalPromotion]: ...

    @abstractmethod
    def fetch_availability(
        self, *, company_code: str, since: datetime | None = None, limit: int = 500
    ) -> list[CanonicalStoreProduct]: ...

    def capabilities(self) -> dict[str, Any]:
        return {"provider": self.name, "read_only": True, "writes_forbidden": True}

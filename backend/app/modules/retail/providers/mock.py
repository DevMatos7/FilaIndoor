from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.modules.retail.dto import (
    CanonicalPrice,
    CanonicalProduct,
    CanonicalPromotion,
    CanonicalStoreProduct,
)
from app.modules.retail.providers.base import RetailDataProvider


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class MockRetailDataProvider(RetailDataProvider):
    name = "mock"

    def __init__(self) -> None:
        now = _utcnow()
        self._products = [
            CanonicalProduct(
                source_product_id="1001:0",
                description="PICANHA BOVINA RESFRIADA",
                commercial_description="PICANHA",
                gtin="7891000100103",
                unit="KG",
                section_code="1",
                section_name="Açougue",
                group_code="10",
                group_name="Bovinos",
                subgroup_code="100",
                subgroup_name="Premium",
                active=True,
                source_updated_at=now,
            ),
            CanonicalProduct(
                source_product_id="1002:0",
                description="ALCATRA BOVINA",
                commercial_description="ALCATRA",
                gtin="7891000100104",
                unit="KG",
                section_code="1",
                section_name="Açougue",
                group_code="10",
                group_name="Bovinos",
                active=True,
                source_updated_at=now,
            ),
            CanonicalProduct(
                source_product_id="2001:0",
                description="BANANA CATURRA",
                commercial_description="BANANA",
                gtin="7891000100201",
                unit="KG",
                section_code="2",
                section_name="Hortifruti",
                group_code="20",
                group_name="Frutas",
                active=True,
                source_updated_at=now,
            ),
            CanonicalProduct(
                source_product_id="9001:0",
                description="PRODUTO INATIVO",
                unit="UN",
                section_code="9",
                active=False,
                source_updated_at=now,
            ),
        ]
        self.company_code = "1"

    def fetch_products(self, *, since: datetime | None = None, limit: int = 500) -> list[CanonicalProduct]:
        return self._products[:limit]

    def fetch_store_products(
        self, *, company_code: str, since: datetime | None = None, limit: int = 500
    ) -> list[CanonicalStoreProduct]:
        now = _utcnow()
        rows = [
            CanonicalStoreProduct("1001:0", company_code, True, True, 42.5, now),
            CanonicalStoreProduct("1002:0", company_code, True, True, 18.0, now),
            CanonicalStoreProduct("2001:0", company_code, True, True, 120.0, now),
            CanonicalStoreProduct("9001:0", company_code, False, False, 0.0, now),
        ]
        return rows[:limit]

    def fetch_prices(
        self, *, company_code: str, since: datetime | None = None, limit: int = 500
    ) -> list[CanonicalPrice]:
        now = _utcnow()
        rows = [
            CanonicalPrice("1001:0", "REGULAR", 69.9, unit="KG", source_ref="mock:regular", source_updated_at=now),
            CanonicalPrice(
                "1001:0",
                "PROMOTION",
                54.9,
                unit="KG",
                starts_at=now - timedelta(days=1),
                expires_at=now + timedelta(days=7),
                source_ref="mock:promo",
                source_updated_at=now,
            ),
            CanonicalPrice("1002:0", "REGULAR", 49.9, unit="KG", source_ref="mock:regular", source_updated_at=now),
            CanonicalPrice(
                "1002:0",
                "PROMOTION",
                44.9,
                unit="KG",
                starts_at=now - timedelta(days=1),
                expires_at=now - timedelta(hours=1),  # expirada
                active=False,
                source_ref="mock:promo-expired",
                source_updated_at=now,
            ),
            CanonicalPrice("2001:0", "REGULAR", 5.99, unit="KG", source_ref="mock:regular", source_updated_at=now),
            CanonicalPrice(
                "2001:0",
                "QUANTITY",
                4.99,
                min_qty=3,
                unit="KG",
                condition_text="A partir de 3 kg",
                source_ref="mock:qty",
                source_updated_at=now,
            ),
            CanonicalPrice(
                "2001:0",
                "QUANTITY",
                3.99,
                min_qty=6,
                unit="KG",
                condition_text="A partir de 6 kg",
                source_ref="mock:qty6",
                source_updated_at=now,
            ),
        ]
        return rows[:limit]

    def fetch_promotions(
        self, *, company_code: str, since: datetime | None = None, limit: int = 500
    ) -> list[CanonicalPromotion]:
        now = _utcnow()
        rows = [
            CanonicalPromotion(
                "1001:0",
                54.9,
                source_promotion_id="promo:1001",
                starts_at=now - timedelta(days=1),
                expires_at=now + timedelta(days=7),
                source_updated_at=now,
            ),
            CanonicalPromotion(
                "1002:0",
                44.9,
                source_promotion_id="promo:1002-expired",
                starts_at=now - timedelta(days=2),
                expires_at=now - timedelta(hours=1),
                active=False,
                source_updated_at=now,
            ),
        ]
        return rows[:limit]

    def fetch_availability(
        self, *, company_code: str, since: datetime | None = None, limit: int = 500
    ) -> list[CanonicalStoreProduct]:
        return self.fetch_store_products(company_code=company_code, since=since, limit=limit)

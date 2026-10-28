from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.modules.integration.providers.base import (
    ERPPrice,
    ERPProduct,
    ERPPromotion,
    ERPProvider,
    ERPStock,
    ERPStore,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class MockERPProvider(ERPProvider):
    """Catálogo demo de açougue — nenhuma I/O externa."""

    name = "mock"

    def __init__(self) -> None:
        now = _utcnow()
        self._stores = {
            "CAMPO_NOVO": ERPStore(
                external_id="CAMPO_NOVO",
                name="Loja Campo Novo",
                company_external_id="REAL",
                stock_location_id="EST-ACOU-1",
            )
        }
        self._products = {
            "SKU-PICANHA": ERPProduct(
                external_product_id="SKU-PICANHA",
                sku="123456",
                ean="7891000100103",
                description="PICANHA BOVINA",
                unit="KG",
                section_code="ACOUGUE",
                group_code="BOVINOS",
                subgroup_code="PREMIUM",
                raw={"demo": True},
            ),
            "SKU-ALCATRA": ERPProduct(
                external_product_id="SKU-ALCATRA",
                sku="123457",
                ean="7891000100104",
                description="ALCATRA BOVINA",
                unit="KG",
                section_code="ACOUGUE",
                group_code="BOVINOS",
                subgroup_code="DIA",
            ),
            "SKU-LINGUICA": ERPProduct(
                external_product_id="SKU-LINGUICA",
                sku="123458",
                ean="7891000100105",
                description="LINGUIÇA TOSCANA",
                unit="KG",
                section_code="ACOUGUE",
                group_code="EMBUTIDOS",
            ),
        }
        self._prices = {
            "SKU-PICANHA": ERPPrice(
                external_product_id="SKU-PICANHA",
                regular_price=69.9,
                promo_price=59.9,
                promo_start=now - timedelta(days=1),
                promo_end=now + timedelta(days=7),
            ),
            "SKU-ALCATRA": ERPPrice(
                external_product_id="SKU-ALCATRA",
                regular_price=49.9,
                promo_price=44.9,
                promo_start=now - timedelta(days=1),
                promo_end=now + timedelta(days=3),
            ),
            "SKU-LINGUICA": ERPPrice(external_product_id="SKU-LINGUICA", regular_price=29.9),
        }
        self._stock = {
            "SKU-PICANHA": ERPStock(external_product_id="SKU-PICANHA", stock_qty=42.5, stock_location_id="EST-ACOU-1"),
            "SKU-ALCATRA": ERPStock(external_product_id="SKU-ALCATRA", stock_qty=18.0, stock_location_id="EST-ACOU-1"),
            "SKU-LINGUICA": ERPStock(external_product_id="SKU-LINGUICA", stock_qty=0.0, stock_location_id="EST-ACOU-1"),
        }

    def get_store(self, external_store_id: str) -> ERPStore | None:
        return self._stores.get(external_store_id)

    def get_product(self, external_product_id: str) -> ERPProduct | None:
        return self._products.get(external_product_id)

    def get_products(self, *, since: datetime | None = None, limit: int = 500) -> list[ERPProduct]:
        return list(self._products.values())[:limit]

    def get_price(self, external_product_id: str, *, store_external_id: str | None = None) -> ERPPrice | None:
        return self._prices.get(external_product_id)

    def get_stock(self, external_product_id: str, *, store_external_id: str | None = None) -> ERPStock | None:
        return self._stock.get(external_product_id)

    def get_promotions(self, *, store_external_id: str | None = None) -> list[ERPPromotion]:
        out: list[ERPPromotion] = []
        for price in self._prices.values():
            if price.promo_price is not None:
                out.append(
                    ERPPromotion(
                        external_product_id=price.external_product_id,
                        promo_price=price.promo_price,
                        promo_start=price.promo_start,
                        promo_end=price.promo_end,
                        label="OFERTA",
                    )
                )
        return out

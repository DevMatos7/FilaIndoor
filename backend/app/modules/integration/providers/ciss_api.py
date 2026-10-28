from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.core.exceptions import ValidationError
from app.modules.integration.providers.base import (
    ERPPrice,
    ERPProduct,
    ERPPromotion,
    ERPProvider,
    ERPStock,
    ERPStore,
)


class CISSApiProvider(ERPProvider):
    """
    Adapter CISSLive / API oficial — SOMENTE LEITURA.

    Sem credenciais configuradas, métodos retornam vazio (não falha o sync).
    Nunca expõe métodos de escrita.
    """

    name = "ciss_api"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key or ""
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def capabilities(self) -> dict[str, Any]:
        caps = super().capabilities()
        caps["configured"] = self.configured
        caps["base_url"] = self.base_url or None
        return caps

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}

    def _get(self, path: str, params: dict | None = None) -> Any:
        if not self.configured:
            return None
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url, headers=self._headers(), params=params or {})
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()

    def get_store(self, external_store_id: str) -> ERPStore | None:
        data = self._get(f"/stores/{external_store_id}")
        if not data:
            return None
        return ERPStore(
            external_id=str(data.get("idLocalEstoque") or data.get("id") or external_store_id),
            name=str(data.get("nome") or data.get("name") or external_store_id),
            company_external_id=str(data["idEmpresa"]) if data.get("idEmpresa") else None,
            stock_location_id=str(data["idLocalEstoque"]) if data.get("idLocalEstoque") else None,
            raw=data if isinstance(data, dict) else None,
        )

    def get_product(self, external_product_id: str) -> ERPProduct | None:
        data = self._get(f"/products/{external_product_id}")
        if not data:
            return None
        return self._map_product(data)

    def get_products(self, *, since: datetime | None = None, limit: int = 500) -> list[ERPProduct]:
        params: dict[str, Any] = {"limit": limit}
        if since:
            params["since"] = since.isoformat()
        data = self._get("/products", params=params)
        if not data:
            return []
        rows = data if isinstance(data, list) else data.get("items") or data.get("data") or []
        return [self._map_product(row) for row in rows if isinstance(row, dict)]

    def get_price(self, external_product_id: str, *, store_external_id: str | None = None) -> ERPPrice | None:
        params = {"store": store_external_id} if store_external_id else None
        data = self._get(f"/products/{external_product_id}/price", params=params)
        if not data:
            return None
        return ERPPrice(
            external_product_id=external_product_id,
            regular_price=_num(data.get("precoRegular") or data.get("regular_price")),
            promo_price=_num(data.get("precoPromocional") or data.get("promo_price")),
            promo_start=_dt(data.get("inicioPromocao") or data.get("promo_start")),
            promo_end=_dt(data.get("fimPromocao") or data.get("promo_end")),
        )

    def get_stock(self, external_product_id: str, *, store_external_id: str | None = None) -> ERPStock | None:
        params = {"store": store_external_id} if store_external_id else None
        data = self._get(f"/products/{external_product_id}/stock", params=params)
        if not data:
            return None
        qty = _num(data.get("saldo") or data.get("stock_qty")) or 0.0
        return ERPStock(
            external_product_id=external_product_id,
            stock_qty=qty,
            stock_location_id=str(data["idLocalEstoque"]) if data.get("idLocalEstoque") else store_external_id,
        )

    def get_promotions(self, *, store_external_id: str | None = None) -> list[ERPPromotion]:
        params = {"store": store_external_id} if store_external_id else None
        data = self._get("/promotions", params=params)
        if not data:
            return []
        rows = data if isinstance(data, list) else data.get("items") or []
        out: list[ERPPromotion] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            pid = str(row.get("idProduto") or row.get("external_product_id") or "")
            price = _num(row.get("precoPromocional") or row.get("promo_price"))
            if not pid or price is None:
                continue
            out.append(
                ERPPromotion(
                    external_product_id=pid,
                    promo_price=price,
                    promo_start=_dt(row.get("inicioPromocao") or row.get("promo_start")),
                    promo_end=_dt(row.get("fimPromocao") or row.get("promo_end")),
                    label=row.get("label") or "OFERTA",
                )
            )
        return out

    def write_forbidden(self, *_args: Any, **_kwargs: Any) -> None:
        raise ValidationError("Gravação no CISS é proibida neste módulo (MVP read-only)")

    def _map_product(self, data: dict[str, Any]) -> ERPProduct:
        return ERPProduct(
            external_product_id=str(data.get("idProduto") or data.get("id") or data.get("sku")),
            sku=str(data["sku"]) if data.get("sku") else None,
            ean=str(data.get("ean") or data.get("EAN") or "") or None,
            description=str(data.get("descricao") or data.get("description") or "Produto"),
            unit=str(data.get("unidade") or data.get("unit") or "UN"),
            section_code=str(data["secao"]) if data.get("secao") else None,
            group_code=str(data["grupo"]) if data.get("grupo") else None,
            subgroup_code=str(data["subgrupo"]) if data.get("subgrupo") else None,
            raw=data,
        )


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    try:
        return datetime.fromisoformat(str(value).replace("Z", ""))
    except ValueError:
        return None

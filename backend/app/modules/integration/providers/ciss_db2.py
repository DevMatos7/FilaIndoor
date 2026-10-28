from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.exceptions import ValidationError
from app.modules.integration.providers.base import (
    ERPPrice,
    ERPProduct,
    ERPPromotion,
    ERPProvider,
    ERPStock,
    ERPStore,
)


class CISSDB2Provider(ERPProvider):
    """
    Leitura DB2 somente leitura — stub seguro.

    Sem DSN configurado não executa SQL. Nunca grava.
    SQL CISS NÃO deve vazar para frontend/signage — só este adapter.
    """

    name = "ciss_db2"

    def __init__(self, *, dsn: str | None = None, read_only: bool = True) -> None:
        self.dsn = dsn or ""
        self.read_only = read_only
        if not self.read_only:
            raise ValidationError("CISSDB2Provider exige read_only=True")

    @property
    def configured(self) -> bool:
        return bool(self.dsn)

    def capabilities(self) -> dict[str, Any]:
        caps = super().capabilities()
        caps["configured"] = self.configured
        caps["read_only"] = True
        caps["note"] = "Configure CISS_DB2_DSN para habilitar consultas; MVP retorna vazio."
        return caps

    def get_store(self, external_store_id: str) -> ERPStore | None:
        self._ensure_no_write()
        return None

    def get_product(self, external_product_id: str) -> ERPProduct | None:
        self._ensure_no_write()
        return None

    def get_products(self, *, since: datetime | None = None, limit: int = 500) -> list[ERPProduct]:
        self._ensure_no_write()
        return []

    def get_price(self, external_product_id: str, *, store_external_id: str | None = None) -> ERPPrice | None:
        self._ensure_no_write()
        return None

    def get_stock(self, external_product_id: str, *, store_external_id: str | None = None) -> ERPStock | None:
        self._ensure_no_write()
        return None

    def get_promotions(self, *, store_external_id: str | None = None) -> list[ERPPromotion]:
        self._ensure_no_write()
        return []

    def _ensure_no_write(self) -> None:
        if not self.read_only:
            raise ValidationError("Escrita DB2 CISS proibida")

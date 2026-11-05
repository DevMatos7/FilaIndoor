from __future__ import annotations

from app.core.config import get_settings
from app.modules.retail.providers.base import RetailDataProvider
from app.modules.retail.providers.ciss_db2 import CissDb2RetailProvider
from app.modules.retail.providers.mock import MockRetailDataProvider


def get_retail_provider(name: str | None = None) -> RetailDataProvider:
    settings = get_settings()
    key = (name or settings.retail_provider or "mock").lower().strip()
    if key in {"ciss_db2", "db2", "ciss"}:
        return CissDb2RetailProvider()
    return MockRetailDataProvider()


__all__ = [
    "RetailDataProvider",
    "MockRetailDataProvider",
    "CissDb2RetailProvider",
    "get_retail_provider",
]

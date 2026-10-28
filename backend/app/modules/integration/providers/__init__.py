from app.core.config import get_settings
from app.modules.integration.providers.base import ERPProvider
from app.modules.integration.providers.ciss_api import CISSApiProvider
from app.modules.integration.providers.ciss_db2 import CISSDB2Provider
from app.modules.integration.providers.mock import MockERPProvider


def get_erp_provider(name: str | None = None) -> ERPProvider:
    settings = get_settings()
    provider = (name or getattr(settings, "erp_provider", None) or "mock").lower()
    if provider == "mock":
        return MockERPProvider()
    if provider in {"ciss_api", "ciss"}:
        return CISSApiProvider(
            base_url=getattr(settings, "ciss_api_base_url", None),
            api_key=getattr(settings, "ciss_api_key", None),
        )
    if provider in {"ciss_db2", "db2"}:
        return CISSDB2Provider(dsn=getattr(settings, "ciss_db2_dsn", None))
    return MockERPProvider()


__all__ = [
    "ERPProvider",
    "MockERPProvider",
    "CISSApiProvider",
    "CISSDB2Provider",
    "get_erp_provider",
]

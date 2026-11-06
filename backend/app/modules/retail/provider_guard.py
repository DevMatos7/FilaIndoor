"""Production safety for RETAIL_PROVIDER — never silent mock prices in prod."""

from __future__ import annotations

import logging

from app.core.config import Settings, get_settings
from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


def retail_provider_is_mock(settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    return (s.retail_provider or "mock").strip().lower() == "mock"


def assert_retail_provider_safe(*, for_automation: bool = False, settings: Settings | None = None) -> None:
    """
    DEV/TEST: mock allowed.
    PRODUCTION: mock forbidden unless retail_allow_mock_in_production (explicit escape hatch).
    """
    s = settings or get_settings()
    if not s.is_production:
        return
    if not retail_provider_is_mock(s):
        return
    if s.retail_allow_mock_in_production:
        logger.warning(
            "retail.provider.mock_allowed_in_production for_automation=%s",
            for_automation,
        )
        return
    msg = (
        "RETAIL_PROVIDER=mock é proibido em produção (APP_ENV=production). "
        "Configure RETAIL_PROVIDER=ciss_db2 ou desative a automação retail. "
        "Preços fictícios nunca devem alimentar Displays."
    )
    logger.error("retail.provider.production_mock_rejected")
    raise ValidationError(msg)


def provider_label(settings: Settings | None = None) -> str:
    s = settings or get_settings()
    key = (s.retail_provider or "mock").strip().upper()
    if key in {"MOCK"}:
        return "MOCK"
    if key in {"CISS_DB2", "CISS"}:
        return "CISS"
    return key

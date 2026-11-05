from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from app.core.config import get_settings


class FreshnessStatus(str, Enum):
    FRESH = "FRESH"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def classify_freshness(
    last_success_at: datetime | None,
    *,
    failed: bool = False,
    warn_after_seconds: int | None = None,
    hard_stop_after_seconds: int | None = None,
) -> FreshnessStatus:
    if failed and not last_success_at:
        return FreshnessStatus.FAILED
    if not last_success_at:
        return FreshnessStatus.UNKNOWN
    settings = get_settings()
    warn = warn_after_seconds if warn_after_seconds is not None else settings.retail_warn_after_seconds
    hard = hard_stop_after_seconds if hard_stop_after_seconds is not None else settings.retail_hard_stop_after_seconds
    age = (utcnow() - last_success_at).total_seconds()
    if failed:
        return FreshnessStatus.FAILED if age >= hard else FreshnessStatus.DEGRADED
    if age <= warn:
        return FreshnessStatus.FRESH
    if age <= hard:
        return FreshnessStatus.DEGRADED
    return FreshnessStatus.STALE


def lag_seconds(last_success_at: datetime | None) -> float | None:
    if not last_success_at:
        return None
    return max(0.0, (utcnow() - last_success_at).total_seconds())

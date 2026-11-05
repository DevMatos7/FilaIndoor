from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.exceptions import ValidationError


def validate_iana_timezone(tz_name: str) -> str:
    name = (tz_name or "").strip()
    if not name:
        raise ValidationError("timezone obrigatório")
    try:
        ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise ValidationError(f"timezone IANA inválido: {name}") from exc
    return name


def _as_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def store_calendar_today(tz_name: str, *, as_of: datetime | None = None) -> date:
    """Calendário civil da loja (IANA). Não usa timezone do browser."""
    tz = ZoneInfo(validate_iana_timezone(tz_name))
    if as_of is None:
        return datetime.now(tz).date()
    if as_of.tzinfo is None:
        return as_of.replace(tzinfo=tz).astimezone(tz).date()
    return as_of.astimezone(tz).date()


def promo_window_active(
    starts: Any,
    ends: Any,
    tz_name: str,
    *,
    as_of: date | datetime | None = None,
) -> bool:
    """CISS DATE fields: active when store-local calendar day is within [start, end] inclusive.

    - before start → inactive
    - start day → active
    - during → active
    - end day → active (inclusive)
    - after end → inactive
    - both bounds missing → inactive
    """
    if isinstance(as_of, datetime):
        today = store_calendar_today(tz_name, as_of=as_of)
    elif isinstance(as_of, date):
        today = as_of
    else:
        today = store_calendar_today(tz_name)

    s = _as_date(starts)
    e = _as_date(ends)
    if s is None and e is None:
        return False
    if s is not None and today < s:
        return False
    if e is not None and today > e:
        return False
    return True

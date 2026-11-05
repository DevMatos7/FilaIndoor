from __future__ import annotations

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

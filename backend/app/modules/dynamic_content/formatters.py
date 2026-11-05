from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


def to_money(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if not d.is_finite():
        return None
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def is_displayable_price(value: Any) -> bool:
    d = to_money(value)
    return d is not None and d > 0


def format_brl(value: Any) -> str | None:
    d = to_money(value)
    if d is None:
        return None
    # pt-BR: 1234.5 → R$ 1.234,50
    sign = "-" if d < 0 else ""
    abs_d = abs(d)
    whole, frac = f"{abs_d:.2f}".split(".")
    parts: list[str] = []
    while whole:
        parts.insert(0, whole[-3:])
        whole = whole[:-3]
    grouped = ".".join(parts)
    return f"{sign}R$ {grouped},{frac}"


def format_unit(unit: str | None) -> str | None:
    if not unit:
        return None
    u = unit.strip().upper()
    if not u:
        return None
    return u.lower()


def format_price_with_unit(amount: Any, unit: str | None, *, show_unit: bool = True) -> str | None:
    money = format_brl(amount)
    if money is None:
        return None
    if not show_unit:
        return money
    u = format_unit(unit)
    if not u:
        return money
    return f"{money} /{u}"


def quantity_condition_text(min_qty: Any, existing: str | None = None) -> str:
    if existing and existing.strip():
        return existing.strip()
    d = to_money(min_qty)
    if d is None:
        return "Faixa por quantidade"
    q = int(d) if d == d.to_integral_value() else float(d)
    return f"{q} ou mais"

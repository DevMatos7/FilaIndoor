from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.org.models.entities import Store
from app.modules.retail.models import RetailPrice, RetailProduct, RetailPromotion
from app.modules.retail.timezone_util import promo_window_active, validate_iana_timezone
from app.modules.dynamic_content.formatters import (
    format_brl,
    format_price_with_unit,
    is_displayable_price,
    quantity_condition_text,
    to_money,
)


@dataclass
class QuantityTierDisplay:
    min_qty: Decimal
    amount: Decimal
    condition_text: str
    formatted_amount: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "min_qty": float(self.min_qty),
            "amount": float(self.amount),
            "condition_text": self.condition_text,
            "formatted_amount": self.formatted_amount,
        }


@dataclass
class PriceDisplay:
    product_id: str
    description: str
    unit: str | None
    regular_price: Decimal | None
    display_price: Decimal | None
    is_promotion: bool
    show_from_to: bool
    promotion_price: Decimal | None
    quantity_tiers: list[QuantityTierDisplay] = field(default_factory=list)
    displayable: bool = False
    formatted_display: str | None = None
    formatted_regular: str | None = None
    formatted_with_unit: str | None = None
    reason: str | None = None

    def as_dict(self, *, show_unit: bool = True) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "description": self.description,
            "unit": self.unit,
            "regular_price": float(self.regular_price) if self.regular_price is not None else None,
            "display_price": float(self.display_price) if self.display_price is not None else None,
            "promotion_price": float(self.promotion_price) if self.promotion_price is not None else None,
            "is_promotion": self.is_promotion,
            "show_from_to": self.show_from_to,
            "quantity_tiers": [t.as_dict() for t in self.quantity_tiers],
            "displayable": self.displayable,
            "formatted_display": self.formatted_display,
            "formatted_regular": self.formatted_regular,
            "formatted_with_unit": format_price_with_unit(self.display_price, self.unit, show_unit=show_unit)
            if self.displayable
            else None,
            "reason": self.reason,
        }


class PriceDisplayResolver:
    """Resolve preço exibível a partir do retail canônico. Nunca no React."""

    def __init__(self, db: Session):
        self.db = db

    def resolve_product(self, store: Store, product: RetailProduct) -> PriceDisplay:
        tz = validate_iana_timezone(store.timezone)
        # TV / player: never use SKU / source_product_id / GTIN as commercial label
        desc = (product.commercial_description or product.description or "").strip()
        unit = (product.unit or "").strip() or None
        banned = {
            (product.source_product_id or "").strip(),
            (product.gtin or "").strip(),
            (getattr(product, "sku", None) or "").strip(),
        }
        banned.discard("")
        if desc and desc in banned:
            desc = ""

        if not desc:
            return PriceDisplay(
                product_id=product.id,
                description="",
                unit=unit,
                regular_price=None,
                display_price=None,
                is_promotion=False,
                show_from_to=False,
                promotion_price=None,
                quantity_tiers=[],
                displayable=False,
                reason="missing_description",
            )

        regular_row = self.db.scalar(
            select(RetailPrice).where(
                RetailPrice.store_id == store.id,
                RetailPrice.product_id == product.id,
                RetailPrice.price_kind == "REGULAR",
                RetailPrice.active.is_(True),
            )
        )
        regular = to_money(regular_row.amount) if regular_row else None
        if regular is not None and regular <= 0:
            regular = None

        promo_row = self.db.scalar(
            select(RetailPromotion).where(
                RetailPromotion.store_id == store.id,
                RetailPromotion.product_id == product.id,
                RetailPromotion.active.is_(True),
            )
        )
        promo_amount = to_money(promo_row.promo_amount) if promo_row else None
        promo_active = False
        if promo_row and promo_amount is not None and promo_amount > 0:
            promo_active = promo_window_active(promo_row.starts_at, promo_row.expires_at, tz)

        qty_rows = list(
            self.db.scalars(
                select(RetailPrice)
                .where(
                    RetailPrice.store_id == store.id,
                    RetailPrice.product_id == product.id,
                    RetailPrice.price_kind == "QUANTITY",
                    RetailPrice.active.is_(True),
                )
                .order_by(RetailPrice.min_qty)
            ).all()
        )
        tiers: list[QuantityTierDisplay] = []
        for q in qty_rows:
            amt = to_money(q.amount)
            mq = to_money(q.min_qty)
            if amt is None or amt <= 0 or mq is None:
                continue
            tiers.append(
                QuantityTierDisplay(
                    min_qty=mq,
                    amount=amt,
                    condition_text=quantity_condition_text(mq, q.condition_text),
                    formatted_amount=format_brl(amt) or "",
                )
            )

        is_promo = bool(promo_active and promo_amount is not None and promo_amount > 0)
        display: Decimal | None = None
        show_from_to = False
        if is_promo:
            display = promo_amount
            if regular is not None and promo_amount is not None and promo_amount < regular:
                show_from_to = True
        elif regular is not None:
            display = regular

        displayable = is_displayable_price(display) or bool(tiers)
        # Quantity-only (no regular) still displayable via tiers
        if not is_displayable_price(display) and tiers:
            display = tiers[0].amount
            displayable = True

        reason = None
        if not displayable:
            reason = "missing_or_invalid_price"

        return PriceDisplay(
            product_id=product.id,
            description=desc,
            unit=unit,
            regular_price=regular,
            display_price=display if is_displayable_price(display) else None,
            is_promotion=is_promo,
            show_from_to=show_from_to,
            promotion_price=promo_amount if is_promo else None,
            quantity_tiers=tiers,
            displayable=displayable and (is_displayable_price(display) or bool(tiers)),
            formatted_display=format_brl(display) if is_displayable_price(display) else None,
            formatted_regular=format_brl(regular) if regular is not None else None,
            reason=reason,
        )

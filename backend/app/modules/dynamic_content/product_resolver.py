from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.modules.dynamic_content.models import DynamicContent, DynamicContentProduct, DynamicContentRule
from app.modules.dynamic_content.price_resolver import PriceDisplay, PriceDisplayResolver
from app.modules.org.models.entities import Store
from app.modules.retail.models import RetailProduct, RetailPromotion, RetailStoreProduct
from app.modules.retail.timezone_util import promo_window_active, validate_iana_timezone


@dataclass
class ResolveResult:
    items: list[PriceDisplay] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    ignored_missing_price: int = 0
    missing_price_product_ids: list[str] = field(default_factory=list)


class DynamicProductResolver:
    def __init__(self, db: Session):
        self.db = db
        self.prices = PriceDisplayResolver(db)

    def resolve(self, content: DynamicContent, store: Store) -> ResolveResult:
        if content.store_id != store.id:
            raise ValidationError("conteúdo não pertence à loja")
        mode = (content.selection_mode or "").upper()
        if mode not in {"MANUAL", "AUTOMATIC", "HYBRID"}:
            raise ValidationError("selection_mode inválido")

        rule = self.db.scalar(
            select(DynamicContentRule).where(DynamicContentRule.dynamic_content_id == content.id)
        )
        if rule and rule.available_only:
            raise ValidationError(
                "available_only não permitido: filtro de estoque desabilitado até validação do local comercial"
            )

        links = list(
            self.db.scalars(
                select(DynamicContentProduct).where(DynamicContentProduct.dynamic_content_id == content.id)
            ).all()
        )
        pinned_ids = [l.product_id for l in links if l.pinned and not l.excluded]
        excluded_ids = {l.product_id for l in links if l.excluded}
        manual_links = sorted(
            [l for l in links if not l.excluded and (mode == "MANUAL" or not l.pinned)],
            key=lambda l: (l.position is None, l.position or 0, l.created_at),
        )
        # For MANUAL, all non-excluded by position
        if mode == "MANUAL":
            ordered_ids = [l.product_id for l in sorted(links, key=lambda l: (l.position is None, l.position or 0)) if not l.excluded]
            return self._materialize(store, ordered_ids, mode="MANUAL")

        auto_ids = self._automatic_ids(store, rule) if mode in {"AUTOMATIC", "HYBRID"} else []

        if mode == "AUTOMATIC":
            return self._materialize(store, auto_ids, mode="AUTOMATIC", limit=rule.limit_items if rule else None)

        # HYBRID: pinned → auto (minus excluded/dupes) → limit
        seen: set[str] = set()
        ordered: list[str] = []
        for pid in pinned_ids:
            if pid in excluded_ids or pid in seen:
                continue
            seen.add(pid)
            ordered.append(pid)
        for pid in auto_ids:
            if pid in excluded_ids or pid in seen:
                continue
            seen.add(pid)
            ordered.append(pid)
        limit = rule.limit_items if rule else None
        return self._materialize(store, ordered, mode="HYBRID", limit=limit, pinned_ids=set(pinned_ids))

    def _automatic_ids(self, store: Store, rule: DynamicContentRule | None) -> list[str]:
        # Products linked to store via retail_store_products
        stmt = (
            select(RetailProduct)
            .join(RetailStoreProduct, RetailStoreProduct.product_id == RetailProduct.id)
            .where(
                RetailStoreProduct.store_id == store.id,
                RetailProduct.active.is_(True),
            )
        )
        if rule:
            if rule.section_code:
                stmt = stmt.where(RetailProduct.section_code == rule.section_code)
            if rule.group_code:
                stmt = stmt.where(RetailProduct.group_code == rule.group_code)
            if rule.subgroup_code:
                stmt = stmt.where(RetailProduct.subgroup_code == rule.subgroup_code)

        products = list(self.db.scalars(stmt).all())
        tz = validate_iana_timezone(store.timezone)

        if rule and rule.promotion_only:
            filtered = []
            for p in products:
                promo = self.db.scalar(
                    select(RetailPromotion).where(
                        RetailPromotion.store_id == store.id,
                        RetailPromotion.product_id == p.id,
                        RetailPromotion.active.is_(True),
                    )
                )
                if promo and promo_window_active(promo.starts_at, promo.expires_at, tz):
                    filtered.append(p)
            products = filtered

        # sort
        sort_mode = (rule.sort_mode if rule else "NAME_ASC") or "NAME_ASC"
        priced = [(p, self.prices.resolve_product(store, p)) for p in products]

        def name_key(pair):
            return (pair[1].description or "").upper()

        def price_key(pair):
            d = pair[1].display_price
            return float(d) if d is not None else 1e18

        if sort_mode == "NAME_ASC":
            priced.sort(key=name_key)
        elif sort_mode == "PRICE_ASC":
            priced.sort(key=price_key)
        elif sort_mode == "PRICE_DESC":
            priced.sort(key=price_key, reverse=True)
        elif sort_mode == "PROMOTION_FIRST":
            priced.sort(key=lambda pair: (0 if pair[1].is_promotion else 1, name_key(pair)))
        else:
            priced.sort(key=name_key)

        return [p.id for p, _ in priced]

    def _materialize(
        self,
        store: Store,
        product_ids: list[str],
        *,
        mode: str,
        limit: int | None = None,
        pinned_ids: set[str] | None = None,
    ) -> ResolveResult:
        result = ResolveResult()
        pinned_ids = pinned_ids or set()
        for pid in product_ids:
            if limit is not None and len(result.items) >= limit:
                break
            prod = self.db.get(RetailProduct, pid)
            if not prod:
                result.warnings.append(f"produto ausente: {pid}")
                continue
            display = self.prices.resolve_product(store, prod)
            if not display.displayable:
                result.ignored_missing_price += 1
                result.missing_price_product_ids.append(pid)
                if mode == "MANUAL" or pid in pinned_ids:
                    result.warnings.append(f"Produto sem preço válido: {display.description}")
                    # keep as non-displayable marker for UI gating
                    result.items.append(display)
                # AUTOMATIC: skip silently (counted)
                continue
            result.items.append(display)
        if result.ignored_missing_price and mode == "AUTOMATIC":
            result.warnings.append(
                f"{result.ignored_missing_price} produto(s) ignorado(s) por ausência de preço"
            )
        return result

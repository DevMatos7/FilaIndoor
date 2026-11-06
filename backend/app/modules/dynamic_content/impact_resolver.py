"""Resolve which DynamicContent rows are affected by retail product changes."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.dynamic_content.models import DynamicContent, DynamicContentProduct, DynamicContentRule
from app.modules.retail.models import RetailProduct


CHANGE_TYPES = {
    "PRODUCT_CHANGED",
    "PRICE_CHANGED",
    "PROMOTION_CHANGED",
    "AVAILABILITY_CHANGED",
    "IMAGE_CHANGED",
}


class DynamicContentImpactResolver:
    def __init__(self, db: Session):
        self.db = db

    def resolve(
        self,
        store_id: str,
        *,
        changed_product_ids: list[str],
        change_types: list[str],
        section_codes: list[str] | None = None,
        group_codes: list[str] | None = None,
        subgroup_codes: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return affected dynamic contents for a store (not global)."""
        types = {c.upper() for c in change_types if c}
        if not types:
            return []
        products = set(changed_product_ids or [])
        sections = set(section_codes or [])
        groups = set(group_codes or [])
        subgroups = set(subgroup_codes or [])

        # Enrich taxonomy from products when missing
        if products and not (sections or groups or subgroups):
            rows = list(
                self.db.scalars(select(RetailProduct).where(RetailProduct.id.in_(list(products)))).all()
            )
            for p in rows:
                if p.section_code:
                    sections.add(p.section_code)
                if p.group_code:
                    groups.add(p.group_code)
                if p.subgroup_code:
                    subgroups.add(p.subgroup_code)

        contents = list(
            self.db.scalars(
                select(DynamicContent).where(
                    DynamicContent.store_id == store_id,
                    DynamicContent.active.is_(True),
                )
            ).all()
        )
        out: list[dict[str, Any]] = []
        for content in contents:
            reason = self._why_affected(
                content,
                products=products,
                types=types,
                sections=sections,
                groups=groups,
                subgroups=subgroups,
            )
            if reason:
                out.append(
                    {
                        "dynamic_content_id": content.id,
                        "name": content.name,
                        "selection_mode": content.selection_mode,
                        "content_type": content.content_type,
                        "reason": reason,
                    }
                )
        return out

    def _why_affected(
        self,
        content: DynamicContent,
        *,
        products: set[str],
        types: set[str],
        sections: set[str],
        groups: set[str],
        subgroups: set[str],
    ) -> str | None:
        mode = (content.selection_mode or "").upper()
        links = list(
            self.db.scalars(
                select(DynamicContentProduct).where(
                    DynamicContentProduct.dynamic_content_id == content.id
                )
            ).all()
        )
        linked_ids = {l.product_id for l in links if not l.excluded}
        pinned_ids = {l.product_id for l in links if l.pinned}

        # MANUAL: only explicit product membership
        if mode == "MANUAL":
            hit = products & linked_ids
            return next(iter(types)) if hit else None

        rule = self.db.scalar(
            select(DynamicContentRule).where(DynamicContentRule.dynamic_content_id == content.id)
        )

        # HYBRID: pinned/excluded products OR rule
        if mode == "HYBRID":
            if products & pinned_ids or products & linked_ids:
                return next(iter(types))
            if self._rule_hit(rule, types=types, sections=sections, groups=groups, subgroups=subgroups):
                return "AUTOMATIC_RULE"
            return None

        # AUTOMATIC
        if mode == "AUTOMATIC":
            if self._rule_hit(rule, types=types, sections=sections, groups=groups, subgroups=subgroups):
                return "AUTOMATIC_RULE"
            # Price/promo changes on unknown membership: if rule has no section filter,
            # invalidate when any commercial change (safer than silent stale)
            if rule and not rule.section_code and not rule.group_code and not rule.subgroup_code:
                if types & {"PRICE_CHANGED", "PROMOTION_CHANGED", "AVAILABILITY_CHANGED"}:
                    return next(iter(types & {"PRICE_CHANGED", "PROMOTION_CHANGED", "AVAILABILITY_CHANGED"}))
            return None

        return None

    @staticmethod
    def _rule_hit(
        rule: DynamicContentRule | None,
        *,
        types: set[str],
        sections: set[str],
        groups: set[str],
        subgroups: set[str],
    ) -> bool:
        if not rule:
            return False
        # promotion_only boards care about promotion changes even without taxonomy match
        if rule.promotion_only and "PROMOTION_CHANGED" in types:
            if not rule.section_code and not rule.group_code and not rule.subgroup_code:
                return True
        matched_tax = False
        if rule.section_code and rule.section_code in sections:
            matched_tax = True
        if rule.group_code and rule.group_code in groups:
            matched_tax = True
        if rule.subgroup_code and rule.subgroup_code in subgroups:
            matched_tax = True
        if rule.section_code or rule.group_code or rule.subgroup_code:
            return matched_tax
        # open rule: any product taxonomy change or commercial change may alter membership
        return bool(types & {"PRODUCT_CHANGED", "PRICE_CHANGED", "PROMOTION_CHANGED", "AVAILABILITY_CHANGED"})

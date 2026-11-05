from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.dynamic_content.models import (
    DynamicContent,
    DynamicContentProduct,
    DynamicContentRule,
    DynamicContentTemplate,
    DynamicRenderSnapshot,
    utcnow,
)
from app.modules.dynamic_content.snapshot_service import SnapshotService
from app.modules.dynamic_content.templates import ensure_system_templates
from app.modules.org.models.entities import Store
from app.modules.retail.models import RetailPrice, RetailProduct, RetailPromotion, RetailStoreProduct
from app.modules.retail.timezone_util import validate_iana_timezone


class DynamicContentService:
    def __init__(self, db: Session):
        self.db = db
        self.snapshots = SnapshotService(db)

    def ensure_templates(self) -> None:
        ensure_system_templates(self.db)

    def list_templates(
        self, *, store_id: str | None = None, content_type: str | None = None, active: bool | None = True
    ) -> list[dict[str, Any]]:
        self.ensure_templates()
        stmt = select(DynamicContentTemplate)
        if active is not None:
            stmt = stmt.where(DynamicContentTemplate.active.is_(active))
        if content_type:
            stmt = stmt.where(DynamicContentTemplate.content_type == content_type)
        rows = list(self.db.scalars(stmt.order_by(DynamicContentTemplate.name)).all())
        out = []
        for r in rows:
            if r.store_id is None or (store_id and r.store_id == store_id):
                out.append(self._template_dict(r))
        return out

    def get_template(self, template_id: str) -> dict[str, Any]:
        self.ensure_templates()
        row = self.db.get(DynamicContentTemplate, template_id)
        if not row or not row.active:
            raise NotFoundError("template não encontrado")
        return self._template_dict(row)

    def list_contents(self, store_id: str) -> list[dict[str, Any]]:
        rows = list(
            self.db.scalars(
                select(DynamicContent)
                .where(DynamicContent.store_id == store_id, DynamicContent.active.is_(True))
                .order_by(DynamicContent.updated_at.desc())
            ).all()
        )
        return [self._content_summary(r) for r in rows]

    def get_content(self, content_id: str, store_id: str) -> dict[str, Any]:
        row = self._get_owned(content_id, store_id)
        return self._content_detail(row)

    def create_content(self, store_id: str, body: dict[str, Any], *, user_id: str | None = None) -> dict[str, Any]:
        store = self._store(store_id)
        validate_iana_timezone(store.timezone)
        self.ensure_templates()
        row = self._apply_body(DynamicContent(store_id=store_id, created_by=user_id), body, creating=True)
        self.db.add(row)
        self.db.flush()
        self._sync_rules_products(row, body)
        self.db.commit()
        self.db.refresh(row)
        return self._content_detail(row)

    def update_content(self, content_id: str, store_id: str, body: dict[str, Any]) -> dict[str, Any]:
        row = self._get_owned(content_id, store_id)
        self._apply_body(row, body, creating=False)
        self._sync_rules_products(row, body, replace=True)
        row.updated_at = utcnow()
        self.db.commit()
        self.db.refresh(row)
        return self._content_detail(row)

    def soft_delete(self, content_id: str, store_id: str) -> dict[str, Any]:
        row = self._get_owned(content_id, store_id)
        row.active = False
        row.updated_at = utcnow()
        self.db.commit()
        return {"id": row.id, "active": False}

    def preview(self, content_id: str, store_id: str) -> dict[str, Any]:
        row = self._get_owned(content_id, store_id)
        store = self._store(store_id)
        return self.snapshots.generate(row, store, persist=True)

    def preview_draft(self, store_id: str, body: dict[str, Any]) -> dict[str, Any]:
        """Preview a partir de draft (persiste temporário e remove — regras no backend)."""
        store = self._store(store_id)
        self.ensure_templates()
        tmp = self._apply_body(
            DynamicContent(store_id=store_id, name=body.get("name") or "Preview", created_by=None),
            body,
            creating=True,
        )
        self.db.add(tmp)
        self.db.flush()
        self._sync_rules_products(tmp, body)
        self.db.flush()
        try:
            payload = self.snapshots.generate(tmp, store, persist=False, allow_stale=False)
        finally:
            self.db.delete(tmp)
            self.db.commit()
        return payload

    def resolve(self, content_id: str, store_id: str) -> dict[str, Any]:
        return self.preview(content_id, store_id)

    def overview(self, store_id: str) -> dict[str, Any]:
        products = self.db.scalar(select(func.count()).select_from(RetailProduct)) or 0
        store_products = (
            self.db.scalar(
                select(func.count()).select_from(RetailStoreProduct).where(RetailStoreProduct.store_id == store_id)
            )
            or 0
        )
        prices = (
            self.db.scalar(
                select(func.count())
                .select_from(RetailPrice)
                .where(RetailPrice.store_id == store_id, RetailPrice.active.is_(True), RetailPrice.price_kind == "REGULAR")
            )
            or 0
        )
        promos = (
            self.db.scalar(
                select(func.count())
                .select_from(RetailPromotion)
                .where(RetailPromotion.store_id == store_id, RetailPromotion.active.is_(True))
            )
            or 0
        )
        tables = (
            self.db.scalar(
                select(func.count())
                .select_from(DynamicContent)
                .where(DynamicContent.store_id == store_id, DynamicContent.active.is_(True))
            )
            or 0
        )
        from app.modules.retail.health_service import RetailHealthService

        health = RetailHealthService(self.db).health(store_id)
        return {
            "products": int(products),
            "store_products": int(store_products),
            "active_regular_prices": int(prices),
            "active_promotions": int(promos),
            "tables": int(tables),
            "ciss_status": health.get("status"),
            "health": health,
        }

    # --- internals ---

    def _store(self, store_id: str) -> Store:
        store = self.db.get(Store, store_id)
        if not store:
            raise NotFoundError("Loja não encontrada")
        return store

    def _get_owned(self, content_id: str, store_id: str) -> DynamicContent:
        row = self.db.get(DynamicContent, content_id)
        if not row or row.store_id != store_id or not row.active:
            raise NotFoundError("conteúdo não encontrado")
        return row

    def _apply_body(self, row: DynamicContent, body: dict[str, Any], *, creating: bool) -> DynamicContent:
        name = (body.get("name") or row.name or "").strip()
        if not name:
            raise ValidationError("name obrigatório")
        mode = (body.get("selection_mode") or row.selection_mode or "").upper()
        if mode not in {"MANUAL", "AUTOMATIC", "HYBRID"}:
            raise ValidationError("selection_mode inválido")
        template_id = body.get("template_id") or row.template_id
        tpl = self.db.get(DynamicContentTemplate, template_id)
        if not tpl or not tpl.active:
            raise ValidationError("template_id inválido")
        if tpl.content_type != "PRICE_TABLE":
            raise ValidationError("apenas PRICE_TABLE neste módulo")
        cfg = dict(row.config or {})
        if body.get("config"):
            cfg.update(body["config"])
        # sanitize display config
        if "available_only" in cfg and cfg["available_only"]:
            raise ValidationError("available_only não permitido neste módulo")
        row.name = name
        row.description = body.get("description", row.description)
        row.content_type = "PRICE_TABLE"
        row.selection_mode = mode
        row.template_id = template_id
        row.config = cfg
        if creating:
            row.active = True
        return row

    def _sync_rules_products(self, row: DynamicContent, body: dict[str, Any], *, replace: bool = False) -> None:
        if replace or "rule" in body:
            existing = list(
                self.db.scalars(select(DynamicContentRule).where(DynamicContentRule.dynamic_content_id == row.id)).all()
            )
            for e in existing:
                self.db.delete(e)
            rule_body = body.get("rule")
            if rule_body:
                if rule_body.get("available_only"):
                    raise ValidationError(
                        "available_only não permitido: estoque comercial ainda não confirmado"
                    )
                self.db.add(
                    DynamicContentRule(
                        dynamic_content_id=row.id,
                        section_code=rule_body.get("section_code"),
                        group_code=rule_body.get("group_code"),
                        subgroup_code=rule_body.get("subgroup_code"),
                        promotion_only=bool(rule_body.get("promotion_only", False)),
                        available_only=False,
                        limit_items=rule_body.get("limit_items"),
                        sort_mode=(rule_body.get("sort_mode") or "NAME_ASC").upper(),
                        config=rule_body.get("config") or {},
                    )
                )

        if replace or "products" in body:
            existing_p = list(
                self.db.scalars(
                    select(DynamicContentProduct).where(DynamicContentProduct.dynamic_content_id == row.id)
                ).all()
            )
            for e in existing_p:
                self.db.delete(e)
            for idx, p in enumerate(body.get("products") or []):
                pid = p.get("product_id")
                prod = self.db.get(RetailProduct, pid)
                if not prod:
                    raise ValidationError(f"produto inválido: {pid}")
                # store isolation: product should exist; optional store_product check for AUTOMATIC handled elsewhere
                self.db.add(
                    DynamicContentProduct(
                        dynamic_content_id=row.id,
                        product_id=pid,
                        position=p.get("position", idx),
                        pinned=bool(p.get("pinned", False)),
                        excluded=bool(p.get("excluded", False)),
                    )
                )

    def _template_dict(self, r: DynamicContentTemplate) -> dict[str, Any]:
        return {
            "id": r.id,
            "store_id": r.store_id,
            "name": r.name,
            "slug": r.slug,
            "content_type": r.content_type,
            "orientation": r.orientation,
            "aspect_ratio": r.aspect_ratio,
            "config": r.config,
            "active": r.active,
            "is_system": r.is_system,
        }

    def _content_summary(self, r: DynamicContent) -> dict[str, Any]:
        tpl = self.db.get(DynamicContentTemplate, r.template_id)
        latest = self.db.scalar(
            select(DynamicRenderSnapshot)
            .where(DynamicRenderSnapshot.dynamic_content_id == r.id)
            .order_by(DynamicRenderSnapshot.generated_at.desc())
            .limit(1)
        )
        return {
            "id": r.id,
            "store_id": r.store_id,
            "name": r.name,
            "selection_mode": r.selection_mode,
            "template_id": r.template_id,
            "template_name": tpl.name if tpl else None,
            "template_slug": tpl.slug if tpl else None,
            "item_count": latest.item_count if latest else None,
            "page_count": latest.page_count if latest else None,
            "total_duration_seconds": (latest.payload or {}).get("pagination", {}).get("total_duration_seconds")
            if latest
            else None,
            "status": (latest.payload or {}).get("status") if latest else "ATENÇÃO",
            "updated_at": r.updated_at.isoformat() + "Z" if r.updated_at else None,
            "active": r.active,
        }

    def _content_detail(self, r: DynamicContent) -> dict[str, Any]:
        rule = self.db.scalar(select(DynamicContentRule).where(DynamicContentRule.dynamic_content_id == r.id))
        products = list(
            self.db.scalars(select(DynamicContentProduct).where(DynamicContentProduct.dynamic_content_id == r.id)).all()
        )
        base = self._content_summary(r)
        base.update(
            {
                "description": r.description,
                "content_type": r.content_type,
                "config": r.config,
                "rule": (
                    {
                        "section_code": rule.section_code,
                        "group_code": rule.group_code,
                        "subgroup_code": rule.subgroup_code,
                        "promotion_only": rule.promotion_only,
                        "available_only": rule.available_only,
                        "limit_items": rule.limit_items,
                        "sort_mode": rule.sort_mode,
                        "config": rule.config,
                    }
                    if rule
                    else None
                ),
                "products": [
                    {
                        "product_id": p.product_id,
                        "position": p.position,
                        "pinned": p.pinned,
                        "excluded": p.excluded,
                    }
                    for p in products
                ],
            }
        )
        return base

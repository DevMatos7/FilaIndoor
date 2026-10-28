from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.modules.integration.models import ProductOfferTemplate
from app.modules.integration.service import IntegrationService
from app.modules.org.models.entities import Store
from app.modules.queue.models.entities import utcnow


class CampaignService:
    """Renderiza ofertas a partir do snapshot local — nunca consulta CISS no frame."""

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.integration = IntegrationService(db)

    def list_templates(self, store_id: str) -> list[dict[str, Any]]:
        rows = self.db.scalars(
            select(ProductOfferTemplate)
            .where(ProductOfferTemplate.store_id == store_id)
            .order_by(ProductOfferTemplate.name)
        ).all()
        return [self._tpl(t) for t in rows]

    def create_template(
        self,
        *,
        store_id: str,
        name: str,
        product_external_id: str,
        template_key: str = "oferta_acougue",
        only_in_stock: bool = True,
        min_stock_qty: float | None = None,
    ) -> dict[str, Any]:
        if not self.db.get(Store, store_id):
            raise NotFoundError("Loja não encontrada")
        product_external_id = product_external_id.strip()
        if not product_external_id:
            raise ValidationError("product_external_id obrigatório")
        tpl = ProductOfferTemplate(
            store_id=store_id,
            name=name.strip() or "Oferta",
            product_external_id=product_external_id,
            template_key=template_key or "oferta_acougue",
            only_in_stock=only_in_stock,
            min_stock_qty=min_stock_qty if min_stock_qty is not None else self.settings.erp_only_in_stock_min_qty,
        )
        self.db.add(tpl)
        self.db.commit()
        self.db.refresh(tpl)
        return self._tpl(tpl)

    def render(self, template_id: str) -> dict[str, Any]:
        tpl = self.db.get(ProductOfferTemplate, template_id)
        if not tpl:
            raise NotFoundError("Template não encontrado")
        snap = self.integration.get_snapshot_for_external(tpl.store_id, tpl.product_external_id)
        if not snap:
            return {
                **self._tpl(tpl),
                "renderable": False,
                "reason": "snapshot_missing",
                "offer": None,
            }

        product = snap["product"]
        stock = snap.get("stock_qty")
        in_stock = stock is None or float(stock) >= float(tpl.min_stock_qty)
        if tpl.only_in_stock and not in_stock:
            return {
                **self._tpl(tpl),
                "renderable": False,
                "reason": "ONLY_IN_STOCK",
                "alert": "Estoque abaixo do limite — campanha ocultada",
                "offer": None,
                "snapshot": snap,
            }

        regular = snap.get("regular_price")
        promo = snap.get("promo_price")
        unit = product.get("unit") or "UN"
        lines = self._render_lines(product["description"], regular, promo, unit, tpl.template_key)
        return {
            **self._tpl(tpl),
            "renderable": True,
            "reason": None,
            "offer": {
                "title": "OFERTA",
                "description": product["description"],
                "sku": product.get("sku"),
                "unit": unit,
                "regular_price": regular,
                "promo_price": promo,
                "lines": lines,
                "stock_qty": stock,
            },
            "snapshot": snap,
            "rendered_at": utcnow().isoformat() + "Z",
        }

    def render_active_for_store(self, store_id: str) -> list[dict[str, Any]]:
        templates = self.db.scalars(
            select(ProductOfferTemplate).where(
                ProductOfferTemplate.store_id == store_id,
                ProductOfferTemplate.active.is_(True),
            )
        ).all()
        return [self.render(t.id) for t in templates]

    def _render_lines(
        self,
        description: str,
        regular: float | None,
        promo: float | None,
        unit: str,
        template_key: str,
    ) -> list[str]:
        unit_suffix = f"/{unit.lower()}" if unit else ""
        if template_key == "oferta_acougue" and promo is not None and regular is not None:
            return [
                description.upper(),
                f"de R$ {regular:.2f}".replace(".", ","),
                f"por R$ {promo:.2f}{unit_suffix}".replace(".", ","),
            ]
        if promo is not None:
            return [description.upper(), f"R$ {promo:.2f}{unit_suffix}".replace(".", ",")]
        if regular is not None:
            return [description.upper(), f"R$ {regular:.2f}{unit_suffix}".replace(".", ",")]
        return [description.upper()]

    def _tpl(self, t: ProductOfferTemplate) -> dict[str, Any]:
        return {
            "id": t.id,
            "store_id": t.store_id,
            "name": t.name,
            "product_external_id": t.product_external_id,
            "template_key": t.template_key,
            "only_in_stock": t.only_in_stock,
            "min_stock_qty": t.min_stock_qty,
            "active": t.active,
        }

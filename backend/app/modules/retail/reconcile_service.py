from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.retail.freshness import utcnow
from app.modules.retail.models import RetailPrice, RetailProduct, RetailPromotion, RetailStoreProduct
from app.modules.retail.providers import get_retail_provider
from app.modules.retail.providers.base import RetailDataProvider
from app.modules.retail.sync_service import RetailSyncService


def _cmp(a: Any, b: Any) -> str:
    if a is None and b is None:
        return "MATCH"
    if a is None or b is None:
        return "NOT_COMPARABLE"
    if isinstance(a, float) and isinstance(b, float):
        return "MATCH" if abs(a - b) < 0.005 else "MISMATCH"
    if isinstance(a, datetime) and isinstance(b, datetime):
        return "MATCH" if a.replace(microsecond=0) == b.replace(microsecond=0) else "MISMATCH"
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            return "MISMATCH"
        for x, y in zip(a, b):
            if _cmp(x, y) != "MATCH":
                return "MISMATCH"
        return "MATCH"
    if isinstance(a, tuple) and isinstance(b, tuple):
        if len(a) != len(b):
            return "MISMATCH"
        for x, y in zip(a, b):
            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                if abs(float(x) - float(y)) >= 0.005:
                    return "MISMATCH"
            elif x != y:
                return "MISMATCH"
        return "MATCH"
    return "MATCH" if a == b else "MISMATCH"


class RetailReconciliationService:
    def __init__(self, db: Session, provider: RetailDataProvider | None = None):
        self.db = db
        self.provider = provider or get_retail_provider()
        self.sync = RetailSyncService(db, provider=self.provider)

    def reconcile(self, store_id: str, product_ids: list[str]) -> dict[str, Any]:
        if not product_ids:
            raise ValidationError("product_ids obrigatório")
        if len(product_ids) > 100:
            raise ValidationError("máximo 100 produtos por reconciliação")
        source = self.sync.get_store_source(store_id)

        # Resolve local products first so we can fetch CISS by exact keys (not only top-N).
        local_products: list[RetailProduct] = []
        for pid in product_ids:
            prod = self.db.get(RetailProduct, pid)
            if prod:
                local_products.append(prod)

        source_ids = [p.source_product_id for p in local_products]
        source_products = {p.source_product_id: p for p in self.provider.fetch_products(limit=5000)}
        if hasattr(self.provider, "fetch_products_by_ids") and source_ids:
            for p in self.provider.fetch_products_by_ids(source_ids):  # type: ignore[attr-defined]
                source_products[p.source_product_id] = p

        if hasattr(self.provider, "fetch_prices_for_products") and source_ids:
            source_prices = self.provider.fetch_prices_for_products(  # type: ignore[attr-defined]
                company_code=source.company_code, source_product_ids=source_ids
            )
        else:
            source_prices = self.provider.fetch_prices(company_code=source.company_code, limit=10000)

        source_promos = [
            p
            for p in (
                self.provider.fetch_promotions(company_code=source.company_code, limit=10000)
                if not hasattr(self.provider, "fetch_prices_for_products")
                else []
            )
        ]
        if hasattr(self.provider, "fetch_prices_for_products"):
            from app.modules.retail.dto import CanonicalPromotion

            for price in source_prices:
                if price.price_kind != "PROMOTION":
                    continue
                source_promos.append(
                    CanonicalPromotion(
                        source_product_id=price.source_product_id,
                        promo_amount=price.amount,
                        source_promotion_id=price.source_ref,
                        starts_at=price.starts_at,
                        expires_at=price.expires_at,
                        active=price.active,
                        source_updated_at=price.source_updated_at,
                    )
                )

        if hasattr(self.provider, "fetch_availability_for_products") and source_ids:
            source_avail = {
                a.source_product_id: a
                for a in self.provider.fetch_availability_for_products(  # type: ignore[attr-defined]
                    company_code=source.company_code, source_product_ids=source_ids
                )
            }
        else:
            source_avail = {
                a.source_product_id: a
                for a in self.provider.fetch_availability(company_code=source.company_code, limit=10000)
            }

        results = []
        for pid in product_ids:
            prod = self.db.get(RetailProduct, pid)
            if not prod:
                results.append({"product_id": pid, "status": "NOT_COMPARABLE", "reason": "product_missing_local"})
                continue
            src = source_products.get(prod.source_product_id)
            fields: dict[str, Any] = {}
            if not src:
                fields["product"] = {"local": prod.description, "source": None, "result": "NOT_COMPARABLE"}
            else:
                fields["product"] = {
                    "local": prod.description,
                    "source": src.description,
                    "result": _cmp(prod.description, src.description),
                }
                fields["unit"] = {
                    "local": prod.unit,
                    "source": src.unit,
                    "result": _cmp(prod.unit, src.unit),
                }

            local_regular = self.db.scalar(
                select(RetailPrice).where(
                    RetailPrice.store_id == store_id,
                    RetailPrice.product_id == prod.id,
                    RetailPrice.price_kind == "REGULAR",
                    RetailPrice.active.is_(True),
                )
            )
            src_regular = next(
                (p for p in source_prices if p.source_product_id == prod.source_product_id and p.price_kind == "REGULAR"),
                None,
            )
            fields["regular_price"] = {
                "local": local_regular.amount if local_regular else None,
                "source": src_regular.amount if src_regular else None,
                "result": _cmp(
                    local_regular.amount if local_regular else None,
                    src_regular.amount if src_regular else None,
                ),
            }

            local_promo = self.db.scalar(
                select(RetailPromotion).where(
                    RetailPromotion.store_id == store_id,
                    RetailPromotion.product_id == prod.id,
                    RetailPromotion.active.is_(True),
                )
            )
            src_promo = next((p for p in source_promos if p.source_product_id == prod.source_product_id and p.active), None)
            # vigência: se local existe, comparar amount; missing ≠ zero
            fields["promotion"] = {
                "local": local_promo.promo_amount if local_promo else None,
                "source": src_promo.promo_amount if src_promo else None,
                "result": _cmp(
                    local_promo.promo_amount if local_promo else None,
                    src_promo.promo_amount if src_promo else None,
                ),
            }
            def _day(dt: Any) -> str | None:
                if not dt:
                    return None
                if isinstance(dt, datetime):
                    return dt.date().isoformat()
                return str(dt)[:10]

            fields["promotion_validity"] = {
                "local_starts": local_promo.starts_at.isoformat() if local_promo and local_promo.starts_at else None,
                "local_expires": local_promo.expires_at.isoformat() if local_promo and local_promo.expires_at else None,
                "source_starts": src_promo.starts_at.isoformat() if src_promo and src_promo.starts_at else None,
                "source_expires": src_promo.expires_at.isoformat() if src_promo and src_promo.expires_at else None,
                # compara calendário (fonte mock regenera timestamps a cada instanciação)
                "result": _cmp(
                    (_day(local_promo.starts_at), _day(local_promo.expires_at)) if local_promo else None,
                    (_day(src_promo.starts_at), _day(src_promo.expires_at)) if src_promo else None,
                ),
            }

            local_qty = list(
                self.db.scalars(
                    select(RetailPrice)
                    .where(
                        RetailPrice.store_id == store_id,
                        RetailPrice.product_id == prod.id,
                        RetailPrice.price_kind == "QUANTITY",
                        RetailPrice.active.is_(True),
                    )
                    .order_by(RetailPrice.min_qty)
                ).all()
            )
            src_qty = sorted(
                [
                    p
                    for p in source_prices
                    if p.source_product_id == prod.source_product_id and p.price_kind == "QUANTITY" and p.active
                ],
                key=lambda p: (p.min_qty or 0),
            )
            local_tiers = [(p.min_qty, p.amount) for p in local_qty]
            source_tiers = [(p.min_qty, p.amount) for p in src_qty]
            fields["quantity_tiers"] = {
                "local": local_tiers,
                "source": source_tiers,
                "result": _cmp(local_tiers, source_tiers) if local_tiers or source_tiers else "MATCH",
            }

            sp = self.db.scalar(
                select(RetailStoreProduct).where(
                    RetailStoreProduct.store_id == store_id,
                    RetailStoreProduct.product_id == prod.id,
                )
            )
            src_av = source_avail.get(prod.source_product_id)
            fields["availability"] = {
                "local": sp.available if sp else None,
                "source": src_av.available if src_av else None,
                "result": _cmp(sp.available if sp else None, src_av.available if src_av else None),
            }

            field_results = [f["result"] for f in fields.values() if isinstance(f, dict) and "result" in f]
            if any(r == "MISMATCH" for r in field_results):
                status = "MISMATCH"
            elif all(r == "MATCH" for r in field_results):
                status = "MATCH"
            else:
                status = "NOT_COMPARABLE"

            results.append(
                {
                    "product_id": prod.id,
                    "source_product_id": prod.source_product_id,
                    "status": status,
                    "fields": fields,
                }
            )

        return {
            "store_id": store_id,
            "reconciled_at": utcnow().isoformat() + "Z",
            "results": results,
            "summary": {
                "match": sum(1 for r in results if r["status"] == "MATCH"),
                "mismatch": sum(1 for r in results if r["status"] == "MISMATCH"),
                "not_comparable": sum(1 for r in results if r["status"] == "NOT_COMPARABLE"),
            },
        }

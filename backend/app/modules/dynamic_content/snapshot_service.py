from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.dynamic_content.models import (
    DynamicContent,
    DynamicContentTemplate,
    DynamicRenderSnapshot,
    utcnow,
)
from app.modules.dynamic_content.product_resolver import DynamicProductResolver, ResolveResult
from app.modules.org.models.entities import Store
from app.modules.retail.health_service import RetailHealthService
from app.modules.retail.models import RetailSyncWatermark


def _stable_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class SnapshotService:
    def __init__(self, db: Session):
        self.db = db
        self.resolver = DynamicProductResolver(db)

    def generate(
        self,
        content: DynamicContent,
        store: Store,
        *,
        persist: bool = True,
        allow_stale: bool = False,
    ) -> dict[str, Any]:
        if content.store_id != store.id:
            raise ValidationError("conteúdo de outra loja")
        template = self.db.get(DynamicContentTemplate, content.template_id)
        if not template or not template.active:
            raise NotFoundError("template não encontrado")

        health = RetailHealthService(self.db).health(store.id)
        freshness = health.get("status") or "UNKNOWN"
        price_entity = next((e for e in health.get("entities", []) if e.get("entity") == "PRICE"), None)
        if price_entity and price_entity.get("status") in {"STALE", "FAILED"}:
            freshness = price_entity["status"]
        elif price_entity and price_entity.get("status") == "DEGRADED" and freshness == "FRESH":
            freshness = "DEGRADED"

        publishable = freshness not in {"STALE", "FAILED"}
        if not publishable and not allow_stale:
            raise ValidationError(
                "Dados de preço desatualizados. A tabela não pode ser considerada pronta para exibição."
            )

        resolved = self.resolver.resolve(content, store)
        cfg = dict(content.config or {})
        tpl_cfg = dict(template.config or {})
        content_type = (content.content_type or template.content_type or "PRICE_TABLE").upper()

        # geometry for visual templates
        cols = int(cfg.get("columns") or tpl_cfg.get("columns") or 0)
        rows_n = int(cfg.get("rows") or tpl_cfg.get("rows") or 0)
        if content_type in {"PRODUCT_GRID", "PROMOTION_BOARD"} and cols and rows_n:
            items_per_page = cols * rows_n
        elif content_type == "PRODUCT_HERO":
            items_per_page = 1
        else:
            items_per_page = int(cfg.get("items_per_page") or tpl_cfg.get("default_items_per_page") or 8)

        min_ipp = int(tpl_cfg.get("min_items_per_page") or 1)
        max_ipp = int(tpl_cfg.get("max_items_per_page") or 40)
        if items_per_page < min_ipp or items_per_page > max_ipp:
            raise ValidationError(f"items_per_page fora do intervalo {min_ipp}–{max_ipp}")

        page_duration = int(cfg.get("page_duration_seconds") or 8)
        if page_duration < 3 or page_duration > 120:
            raise ValidationError("page_duration_seconds deve estar entre 3 e 120")

        duration_mode = (cfg.get("duration_mode") or "FULL_CYCLE").upper()
        if duration_mode not in {"FULL_CYCLE", "FIXED"}:
            raise ValidationError("duration_mode inválido")

        show_unit = bool(cfg.get("show_unit", tpl_cfg.get("show_unit", True)))
        display_items = [i for i in resolved.items if i.displayable]
        blocking_missing = [i for i in resolved.items if not i.displayable]
        item_count = len(display_items)
        page_count = max(1, math.ceil(item_count / items_per_page)) if item_count else 1

        if duration_mode == "FULL_CYCLE":
            total_duration = page_count * page_duration
        else:
            total_duration = int(cfg.get("total_duration_seconds") or (page_count * page_duration))
            if total_duration < 3:
                raise ValidationError("total_duration_seconds inválido")

        # Batch product images for visual types (and optional PRICE_TABLE)
        from app.modules.retail.product_media_service import ProductMediaService

        image_map = ProductMediaService(self.db).batch_primary_images(
            [i.product_id for i in display_items], store.id
        )

        pages = []
        for page_no in range(page_count):
            start = page_no * items_per_page
            chunk = display_items[start : start + items_per_page]
            page_items = []
            for it in chunk:
                d = it.as_dict(show_unit=show_unit)
                img = image_map.get(it.product_id)
                d["image"] = img  # None → renderer fallback
                page_items.append(d)
            pages.append({"number": page_no + 1, "items": page_items})

        hash_basis = {
            "content_id": content.id,
            "content_type": content_type,
            "name": content.name,
            "selection_mode": content.selection_mode,
            "template_slug": template.slug,
            "config": cfg,
            "items": [
                {
                    "product_id": i.product_id,
                    "display_price": str(i.display_price) if i.display_price is not None else None,
                    "regular_price": str(i.regular_price) if i.regular_price is not None else None,
                    "is_promotion": i.is_promotion,
                    "tiers": [(str(t.min_qty), str(t.amount)) for t in i.quantity_tiers],
                    "unit": i.unit,
                    "description": i.description,
                    "image_asset_id": (image_map.get(i.product_id) or {}).get("asset_id"),
                }
                for i in display_items
            ],
        }
        content_hash = _stable_hash(hash_basis)
        data_version = self._data_version(store.id)

        warnings = list(resolved.warnings)
        if freshness == "DEGRADED":
            warnings.append("Dados de preço em estado DEGRADED — preview permitido com atenção.")
        if blocking_missing and content.selection_mode.upper() in {"MANUAL", "HYBRID"}:
            warnings.append("Existem produtos sem preço válido; conteúdo não está PRONTO.")
        if item_count == 0 and content_type == "PROMOTION_BOARD":
            warnings.append("Nenhuma promoção vigente encontrada.")

        status = self._table_status(content, freshness, blocking_missing, item_count)

        payload = {
            "content_type": content_type,
            "title": cfg.get("title") or content.name,
            "template": {"id": template.id, "slug": template.slug, "name": template.name, "config": tpl_cfg},
            "source": {
                "freshness": freshness,
                "generated_at": utcnow().isoformat() + "Z",
                "data_version": data_version,
                "provider": "CISS",
            },
            "selection_mode": content.selection_mode,
            "pagination": {
                "items_per_page": items_per_page,
                "page_count": page_count,
                "page_duration_seconds": page_duration,
                "duration_mode": duration_mode,
                "total_duration_seconds": total_duration,
                "columns": cols or tpl_cfg.get("columns"),
                "rows": rows_n or tpl_cfg.get("rows"),
            },
            "pages": pages,
            "item_count": item_count,
            "warnings": warnings,
            "status": status,
            "ignored_missing_price": resolved.ignored_missing_price,
            "missing_price_product_ids": resolved.missing_price_product_ids,
            "content_hash": content_hash,
            "image_fit": cfg.get("image_fit") or tpl_cfg.get("image_fit") or "contain",
            "show_image": bool(cfg.get("show_image", tpl_cfg.get("show_image", True))),
        }

        # Empty visual boards are not publishable for TV
        publishable_final = publishable and status == "PRONTA" and item_count > 0

        if persist and publishable:
            snap = DynamicRenderSnapshot(
                dynamic_content_id=content.id,
                store_id=store.id,
                content_hash=content_hash,
                data_version=data_version,
                payload=payload,
                item_count=item_count,
                page_count=page_count,
                source_freshness=freshness,
                publishable=publishable_final,
                warnings=warnings,
            )
            self.db.add(snap)
            self.db.commit()
            self.db.refresh(snap)
            payload["snapshot_id"] = snap.id

        return payload

    def ensure_current_snapshot(
        self,
        content: DynamicContent,
        store: Store,
        *,
        allow_stale: bool = False,
    ) -> dict[str, Any]:
        """Return publishable payload regenerated when data_version drifts."""
        if content.store_id != store.id:
            raise ValidationError("conteúdo de outra loja")
        if not content.active:
            raise ValidationError("conteúdo inativo")

        current_version = self._data_version(store.id)
        latest = self.db.scalar(
            select(DynamicRenderSnapshot)
            .where(DynamicRenderSnapshot.dynamic_content_id == content.id)
            .order_by(DynamicRenderSnapshot.generated_at.desc())
            .limit(1)
        )
        if (
            latest
            and latest.data_version == current_version
            and latest.publishable
            and isinstance(latest.payload, dict)
            and (latest.payload.get("source") or {}).get("freshness") not in {"STALE", "FAILED"}
        ):
            payload = dict(latest.payload)
            payload["snapshot_id"] = latest.id
            return payload

        return self.generate(content, store, persist=True, allow_stale=allow_stale)

    def player_payload(self, snapshot: dict[str, Any], *, content_id: str, name: str) -> dict[str, Any]:
        """Strip admin-only meta for Display Player."""
        pag = snapshot.get("pagination") or {}
        src = snapshot.get("source") or {}
        tpl = snapshot.get("template") or {}
        ctype = snapshot.get("content_type") or "PRICE_TABLE"
        return {
            "id": content_id,
            "type": ctype,
            "content_type": ctype,
            "name": name,
            "version": snapshot.get("content_hash") or snapshot.get("snapshot_id"),
            "generated_at": src.get("generated_at"),
            "freshness": src.get("freshness"),
            "valid_until": self._valid_until(src.get("freshness")),
            "duration_mode": pag.get("duration_mode"),
            "page_duration_seconds": pag.get("page_duration_seconds"),
            "total_duration_seconds": pag.get("total_duration_seconds"),
            "page_count": pag.get("page_count"),
            "item_count": snapshot.get("item_count"),
            "status": snapshot.get("status"),
            "title": snapshot.get("title") or name,
            "image_fit": snapshot.get("image_fit") or "contain",
            "show_image": snapshot.get("show_image", True),
            "template": {
                "id": tpl.get("id"),
                "slug": tpl.get("slug"),
                "name": tpl.get("name"),
                "config": {
                    k: v
                    for k, v in (tpl.get("config") or {}).items()
                    if k
                    in {
                        "columns",
                        "rows",
                        "emphasize_promo",
                        "show_unit",
                        "show_image",
                        "show_regular_price",
                        "show_promo_badge",
                        "image_fit",
                        "hero_layout",
                        "default_items_per_page",
                    }
                },
            },
            "pages": snapshot.get("pages") or [],
            "content_hash": snapshot.get("content_hash"),
            "data_version": src.get("data_version"),
        }

    def _valid_until(self, freshness: str | None) -> str:
        """MVP TTL window for offline cache — not indefinite prices."""
        from datetime import timedelta

        now = utcnow()
        # FRESH/DEGRADED: 15 min; otherwise immediate expiry signal
        minutes = 15 if freshness in {"FRESH", "DEGRADED", None} else 0
        return (now + timedelta(minutes=minutes)).isoformat() + "Z"

    def _data_version(self, store_id: str) -> str:
        rows = list(
            self.db.scalars(
                select(RetailSyncWatermark).where(
                    RetailSyncWatermark.store_id == store_id,
                    RetailSyncWatermark.source_system == "CISS",
                )
            ).all()
        )
        parts = []
        for r in sorted(rows, key=lambda x: x.entity):
            parts.append(f"{r.entity}:{r.watermark_value or ''}:{r.last_success_at.isoformat() if r.last_success_at else ''}")
        # Product media changes must invalidate snapshots (hash includes image ids)
        from sqlalchemy import func

        from app.modules.retail.models import ProductMediaLink

        media_max = self.db.scalar(
            select(func.max(ProductMediaLink.updated_at)).where(
                (ProductMediaLink.store_id == store_id) | (ProductMediaLink.store_id.is_(None)),
                ProductMediaLink.active.is_(True),
            )
        )
        media_cnt = self.db.scalar(
            select(func.count()).select_from(ProductMediaLink).where(
                (ProductMediaLink.store_id == store_id) | (ProductMediaLink.store_id.is_(None)),
                ProductMediaLink.active.is_(True),
            )
        )
        parts.append(f"MEDIA:{media_cnt}:{media_max.isoformat() if media_max else ''}")
        raw = "|".join(parts) or "none"
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    def _table_status(
        self,
        content: DynamicContent,
        freshness: str,
        blocking_missing: list,
        item_count: int,
    ) -> str:
        if not content.active:
            return "INATIVA"
        if freshness in {"STALE", "FAILED"}:
            return "DADOS DESATUALIZADOS"
        if blocking_missing and content.selection_mode.upper() in {"MANUAL", "HYBRID"}:
            return "ATENÇÃO"
        if item_count == 0:
            return "ATENÇÃO"
        if freshness == "DEGRADED":
            return "ATENÇÃO"
        return "PRONTA"

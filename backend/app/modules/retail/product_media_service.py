from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.modules.retail.models import ProductMediaLink, RetailProduct, utcnow
from app.modules.signage.models import MediaAsset
from app.modules.signage.service import asset_to_dict


class ProductMediaService:
    """Product ↔ MediaAsset links. MANUAL only in Module 4."""

    def __init__(self, db: Session):
        self.db = db

    def list_for_product(self, product_id: str, *, store_id: str | None = None) -> list[dict[str, Any]]:
        prod = self.db.get(RetailProduct, product_id)
        if not prod:
            raise NotFoundError("Produto não encontrado")
        stmt = (
            select(ProductMediaLink)
            .where(ProductMediaLink.product_id == product_id, ProductMediaLink.active.is_(True))
            .order_by(ProductMediaLink.is_primary.desc(), ProductMediaLink.created_at.desc())
        )
        if store_id:
            # include store-specific + global
            stmt = stmt.where(
                (ProductMediaLink.store_id == store_id) | (ProductMediaLink.store_id.is_(None))
            )
        rows = list(self.db.scalars(stmt).all())
        return [self._link_dict(r) for r in rows]

    def attach(
        self,
        product_id: str,
        *,
        media_asset_id: str,
        store_id: str | None,
        purpose: str = "PRIMARY",
        is_primary: bool = True,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        prod = self.db.get(RetailProduct, product_id)
        if not prod:
            raise NotFoundError("Produto não encontrado")
        purpose = (purpose or "PRIMARY").upper()
        if purpose not in {"PRIMARY", "SECONDARY", "BACKGROUND"}:
            raise ValidationError("purpose inválido")

        asset = self.db.get(MediaAsset, media_asset_id)
        if not asset or not asset.active:
            raise NotFoundError("Mídia não encontrada")
        if asset.media_type != "IMAGE":
            raise ValidationError("Somente IMAGE pode ser associada como imagem de produto")
        if store_id and asset.store_id != store_id:
            raise ForbiddenError("Mídia pertence a outra loja")
        if not store_id and asset.store_id:
            # global product link still requires asset from a concrete store in this domain —
            # allow if caller explicitly sets store_id=NULL only when asset store matches context later;
            # MVP: require store_id for attach to avoid silent cross-store
            raise ValidationError("store_id obrigatório para associação de imagem (domínio por loja)")

        link = ProductMediaLink(
            product_id=product_id,
            store_id=store_id,
            media_asset_id=asset.id,
            purpose=purpose,
            source="MANUAL",
            is_primary=bool(is_primary),
            verified=False,
            active=True,
            created_by=user_id,
        )
        self.db.add(link)
        self.db.flush()
        if link.is_primary:
            self._clear_other_primaries(product_id, store_id=store_id, keep_id=link.id, purpose=purpose)
        self.db.commit()
        self.db.refresh(link)
        if link.is_primary and store_id:
            self._invalidate_visual(store_id, product_id)
        return self._link_dict(link)

    def patch_link(
        self,
        product_id: str,
        link_id: str,
        *,
        store_id: str | None = None,
        is_primary: bool | None = None,
        purpose: str | None = None,
        active: bool | None = None,
    ) -> dict[str, Any]:
        link = self._get_link(product_id, link_id)
        if store_id is not None and link.store_id not in (None, store_id):
            raise ForbiddenError("Vínculo de outra loja")
        if purpose is not None:
            p = purpose.upper()
            if p not in {"PRIMARY", "SECONDARY", "BACKGROUND"}:
                raise ValidationError("purpose inválido")
            link.purpose = p
        if active is not None:
            link.active = active
        if is_primary is True:
            link.is_primary = True
            self._clear_other_primaries(
                product_id, store_id=link.store_id, keep_id=link.id, purpose=link.purpose
            )
        elif is_primary is False:
            link.is_primary = False
        link.updated_at = utcnow()
        self.db.commit()
        self.db.refresh(link)
        sid = store_id or link.store_id
        if sid and link.is_primary:
            self._invalidate_visual(sid, product_id)
        return self._link_dict(link)

    def detach(self, product_id: str, link_id: str, *, store_id: str | None = None) -> dict[str, Any]:
        link = self._get_link(product_id, link_id)
        if store_id is not None and link.store_id not in (None, store_id):
            raise ForbiddenError("Vínculo de outra loja")
        was_primary = link.is_primary
        sid = store_id or link.store_id
        link.active = False
        link.updated_at = utcnow()
        self.db.commit()
        if was_primary and sid:
            self._invalidate_visual(sid, product_id)
        return {"id": link_id, "active": False}

    def _invalidate_visual(self, store_id: str, product_id: str) -> None:
        try:
            from app.modules.dynamic_content.invalidation_service import DynamicInvalidationService

            DynamicInvalidationService(self.db).invalidate_products(
                store_id,
                changed_product_ids=[product_id],
                change_types=["IMAGE_CHANGED"],
            )
        except Exception:  # noqa: BLE001
            pass

    def resolve_primary_image(self, product_id: str, store_id: str) -> dict[str, Any] | None:
        """Precedence: MANUAL store > CISS store > MANUAL global > CISS global."""
        candidates = list(
            self.db.scalars(
                select(ProductMediaLink).where(
                    ProductMediaLink.product_id == product_id,
                    ProductMediaLink.purpose == "PRIMARY",
                    ProductMediaLink.is_primary.is_(True),
                    ProductMediaLink.active.is_(True),
                    (ProductMediaLink.store_id == store_id) | (ProductMediaLink.store_id.is_(None)),
                )
            ).all()
        )

        def rank(link: ProductMediaLink) -> tuple[int, int]:
            store_rank = 0 if link.store_id == store_id else 1
            src = (link.source or "MANUAL").upper()
            source_rank = 0 if src == "MANUAL" else (1 if src == "CISS" else 2)
            return (store_rank, source_rank)

        link = sorted(candidates, key=rank)[0] if candidates else None
        if not link:
            return None
        asset = self.db.get(MediaAsset, link.media_asset_id)
        if not asset or not asset.active or asset.media_type != "IMAGE":
            return None
        # store isolation: store-scoped asset must match
        if link.store_id and asset.store_id != link.store_id:
            return None
        if not link.store_id and asset.store_id != store_id:
            # global link pointing at foreign store asset — reject
            return None
        return {"asset_id": asset.id, "url": asset.public_url, "name": asset.name}

    def batch_primary_images(self, product_ids: list[str], store_id: str) -> dict[str, dict[str, Any]]:
        """Batch resolve without N+1."""
        if not product_ids:
            return {}
        links = list(
            self.db.scalars(
                select(ProductMediaLink).where(
                    ProductMediaLink.product_id.in_(product_ids),
                    ProductMediaLink.purpose == "PRIMARY",
                    ProductMediaLink.is_primary.is_(True),
                    ProductMediaLink.active.is_(True),
                    (ProductMediaLink.store_id == store_id) | (ProductMediaLink.store_id.is_(None)),
                )
            ).all()
        )
        # prefer store-specific MANUAL over CISS, then global
        def _rank(link: ProductMediaLink) -> tuple[int, int]:
            store_rank = 0 if link.store_id == store_id else 1
            src = (link.source or "MANUAL").upper()
            source_rank = 0 if src == "MANUAL" else (1 if src == "CISS" else 2)
            return (store_rank, source_rank)

        chosen: dict[str, ProductMediaLink] = {}
        for link in sorted(links, key=_rank):
            if link.product_id not in chosen:
                chosen[link.product_id] = link

        asset_ids = [l.media_asset_id for l in chosen.values()]
        assets = {
            a.id: a
            for a in self.db.scalars(
                select(MediaAsset).where(MediaAsset.id.in_(asset_ids), MediaAsset.active.is_(True))
            ).all()
            if asset_ids
        }
        out: dict[str, dict[str, Any]] = {}
        for pid, link in chosen.items():
            asset = assets.get(link.media_asset_id)
            if not asset or asset.media_type != "IMAGE":
                continue
            if link.store_id and asset.store_id != link.store_id:
                continue
            if not link.store_id and asset.store_id != store_id:
                continue
            out[pid] = {"asset_id": asset.id, "url": asset.public_url, "name": asset.name}
        return out

    def count_usage_for_assets(self, asset_ids: list[str]) -> dict[str, int]:
        if not asset_ids:
            return {}
        rows = self.db.execute(
            select(ProductMediaLink.media_asset_id, func.count())
            .where(
                ProductMediaLink.media_asset_id.in_(asset_ids),
                ProductMediaLink.active.is_(True),
            )
            .group_by(ProductMediaLink.media_asset_id)
        ).all()
        return {str(aid): int(cnt) for aid, cnt in rows}

    def _get_link(self, product_id: str, link_id: str) -> ProductMediaLink:
        link = self.db.get(ProductMediaLink, link_id)
        if not link or link.product_id != product_id or not link.active:
            raise NotFoundError("Vínculo de imagem não encontrado")
        return link

    def _clear_other_primaries(
        self, product_id: str, *, store_id: str | None, keep_id: str, purpose: str
    ) -> None:
        stmt = select(ProductMediaLink).where(
            ProductMediaLink.product_id == product_id,
            ProductMediaLink.purpose == purpose,
            ProductMediaLink.active.is_(True),
            ProductMediaLink.id != keep_id,
            ProductMediaLink.is_primary.is_(True),
        )
        if store_id is None:
            stmt = stmt.where(ProductMediaLink.store_id.is_(None))
        else:
            stmt = stmt.where(ProductMediaLink.store_id == store_id)
        for row in self.db.scalars(stmt).all():
            row.is_primary = False
            row.updated_at = utcnow()

    def _link_dict(self, link: ProductMediaLink) -> dict[str, Any]:
        asset = self.db.get(MediaAsset, link.media_asset_id)
        return {
            "id": link.id,
            "product_id": link.product_id,
            "store_id": link.store_id,
            "media_asset_id": link.media_asset_id,
            "purpose": link.purpose,
            "source": link.source,
            "is_primary": link.is_primary,
            "verified": link.verified,
            "active": link.active,
            "created_at": link.created_at.isoformat() + "Z" if link.created_at else None,
            "updated_at": link.updated_at.isoformat() + "Z" if link.updated_at else None,
            "asset": asset_to_dict(asset) if asset else None,
        }

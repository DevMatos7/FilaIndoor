"""Seed Dynamic Content + playlist for Module 6 visual/E2E gate (Campo Novo)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.db.session import SessionLocal
from app.modules.dynamic_content.content_service import DynamicContentService
from app.modules.dynamic_content.models import DynamicContentTemplate
from app.modules.dynamic_content.templates import ensure_system_templates
from app.modules.org.models.entities import Store
from app.modules.queue import models as queue_models  # noqa: F401
from app.modules.retail import models as retail_models  # noqa: F401
from app.modules.retail.models import (
    ProductMediaLink,
    RetailOfferCampaign,
    RetailOfferItem,
    RetailPrice,
    RetailProduct,
)
from app.modules.retail.offer_sync_service import RetailOfferSyncService
from app.modules.retail.providers.ciss_db2 import CissDb2RetailProvider
from app.modules.retail.sync_service import RetailSyncService
from app.modules.signage.models import MediaAsset, Playlist, PlaylistItem

OUT = REPO / "frontend" / "e2e" / ".auth" / "drc6-seed.json"


def main() -> int:
    db = SessionLocal()
    try:
        store = db.scalar(select(Store).where(Store.name.ilike("%Campo Novo%")))
        assert store, "Loja Campo Novo não encontrada"
        provider = CissDb2RetailProvider()
        sync = RetailSyncService(db, provider=provider)
        sync.upsert_store_source(store.id, company_code="1")
        RetailOfferSyncService(db, provider=provider).sync_offers(store.id, company_code="1", limit=10)

        ensure_system_templates(db)
        svc = DynamicContentService(db)

        # Products with CISS images preferred
        linked = list(
            db.scalars(
                select(RetailProduct)
                .join(ProductMediaLink, ProductMediaLink.product_id == RetailProduct.id)
                .where(
                    ProductMediaLink.store_id == store.id,
                    ProductMediaLink.source == "CISS",
                    ProductMediaLink.active.is_(True),
                    RetailProduct.active.is_(True),
                )
                .limit(12)
            ).all()
        )
        if len(linked) < 4:
            linked = list(
                db.scalars(select(RetailProduct).where(RetailProduct.active.is_(True)).limit(12)).all()
            )
        priced = []
        for p in linked:
            rp = db.scalar(
                select(RetailPrice).where(
                    RetailPrice.product_id == p.id,
                    RetailPrice.store_id == store.id,
                    RetailPrice.price_kind == "REGULAR",
                    RetailPrice.active.is_(True),
                )
            )
            if rp:
                priced.append(p)
        products = priced or linked
        assert len(products) >= 2, "Produtos insuficientes"

        def tpl(slug: str) -> DynamicContentTemplate:
            row = db.scalar(select(DynamicContentTemplate).where(DynamicContentTemplate.slug == slug))
            assert row, f"template {slug}"
            return row

        stamp = datetime.now(timezone.utc).strftime("%H%M%S")
        contents: dict[str, str] = {}

        table = svc.create_content(
            store.id,
            {
                "name": f"DRC6 PRICE_TABLE {stamp}",
                "content_type": "PRICE_TABLE",
                "selection_mode": "MANUAL",
                "template_id": tpl("price_table_clean").id,
                "config": {
                    "title": "Tabela DRC6",
                    "items_per_page": 8,
                    "page_duration_seconds": 8,
                    "duration_mode": "FULL_CYCLE",
                },
                "products": [{"product_id": p.id, "position": i} for i, p in enumerate(products[:8])],
            },
        )
        contents["price_table"] = table["id"]

        grid22 = svc.create_content(
            store.id,
            {
                "name": f"DRC6 GRID 2x2 {stamp}",
                "content_type": "PRODUCT_GRID",
                "selection_mode": "MANUAL",
                "template_id": tpl("product_grid_2x2").id,
                "config": {"title": "Grade 2x2", "items_per_page": 4, "page_duration_seconds": 8},
                "products": [{"product_id": p.id, "position": i} for i, p in enumerate(products[:4])],
            },
        )
        contents["grid_2x2"] = grid22["id"]

        grid42_tpl = db.scalar(
            select(DynamicContentTemplate).where(DynamicContentTemplate.slug == "product_grid_4x2")
        ) or tpl("product_grid_2x2")
        grid42 = svc.create_content(
            store.id,
            {
                "name": f"DRC6 GRID 4x2 {stamp}",
                "content_type": "PRODUCT_GRID",
                "selection_mode": "MANUAL",
                "template_id": grid42_tpl.id,
                "config": {"title": "Grade 4x2", "items_per_page": 8, "page_duration_seconds": 8},
                "products": [{"product_id": p.id, "position": i} for i, p in enumerate(products[:8])],
            },
        )
        contents["grid_4x2"] = grid42["id"]

        hero_tpl = db.scalar(
            select(DynamicContentTemplate).where(DynamicContentTemplate.slug == "product_hero_clean")
        ) or tpl("product_grid_2x2")
        hero = svc.create_content(
            store.id,
            {
                "name": f"DRC6 HERO {stamp}",
                "content_type": "PRODUCT_HERO",
                "selection_mode": "MANUAL",
                "template_id": hero_tpl.id,
                "config": {"title": "Destaque", "page_duration_seconds": 8},
                "products": [{"product_id": products[0].id, "position": 0}],
            },
        )
        contents["hero"] = hero["id"]

        now = datetime.utcnow()
        campaign = db.scalar(
            select(RetailOfferCampaign).where(
                RetailOfferCampaign.store_id == store.id,
                RetailOfferCampaign.active.is_(True),
                RetailOfferCampaign.starts_at <= now,
                RetailOfferCampaign.expires_at >= now,
            )
        )
        board_id = None
        if campaign:
            board_tpl = db.scalar(
                select(DynamicContentTemplate).where(
                    DynamicContentTemplate.slug == "promotion_board_2x2"
                )
            )
            if board_tpl:
                board = svc.create_content(
                    store.id,
                    {
                        "name": f"DRC6 CISS_OFFER {stamp}",
                        "content_type": "PROMOTION_BOARD",
                        "selection_mode": "AUTOMATIC",
                        "template_id": board_tpl.id,
                        "config": {"items_per_page": 4, "page_duration_seconds": 8},
                        "rule": {
                            "promotion_only": True,
                            "available_only": False,
                            "limit_items": 8,
                            "sort_mode": "NAME_ASC",
                            "config": {
                                "selection_source": "CISS_OFFER",
                                "offer_campaign_id": campaign.id,
                            },
                        },
                    },
                )
                board_id = board["id"]
                contents["promotion_board"] = board_id

        for cid in contents.values():
            try:
                svc.resolve(cid, store.id)
            except Exception:
                pass

        # Mixed playlist
        media = db.scalar(
            select(MediaAsset).where(
                MediaAsset.store_id == store.id,
                MediaAsset.active.is_(True),
                MediaAsset.media_type == "IMAGE",
            )
        )
        pl = Playlist(store_id=store.id, name=f"DRC6 Mixed {stamp}", is_default=False, active=True)
        db.add(pl)
        db.flush()
        pos = 0
        if media:
            db.add(
                PlaylistItem(
                    playlist_id=pl.id,
                    item_type="MEDIA",
                    asset_id=media.id,
                    duration_seconds=5,
                    position=pos,
                    active=True,
                )
            )
            pos += 1
        for key in ("price_table", "grid_2x2", "hero", "promotion_board"):
            cid = contents.get(key)
            if not cid:
                continue
            db.add(
                PlaylistItem(
                    playlist_id=pl.id,
                    item_type="DYNAMIC",
                    dynamic_content_id=cid,
                    position=pos,
                    active=True,
                )
            )
            pos += 1
        db.commit()

        items_n = 0
        if campaign:
            items_n = len(
                list(
                    db.scalars(
                        select(RetailOfferItem).where(
                            RetailOfferItem.campaign_id == campaign.id,
                            RetailOfferItem.active.is_(True),
                        )
                    ).all()
                )
            )

        payload = {
            "store_id": store.id,
            "store_name": store.name,
            "timezone": store.timezone,
            "contents": contents,
            "playlist_id": pl.id,
            "offer_campaign_id": campaign.id if campaign else None,
            "offer_name": campaign.name if campaign else None,
            "offer_items": items_n,
            "ciss_image_products": [p.id for p in products[:8]],
            "seeded_at": datetime.now(timezone.utc).isoformat(),
        }
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps({"ok": True, "out": str(OUT), **payload}, ensure_ascii=False, default=str))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    # hero template slug may vary — soft resolve
    raise SystemExit(main())

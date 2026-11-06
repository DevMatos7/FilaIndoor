"""DRC-5R — offer price resolver, image precedence, offer models."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.modules.dynamic_content.content_service import DynamicContentService
from app.modules.dynamic_content.models import DynamicContentTemplate
from app.modules.dynamic_content.product_resolver import DynamicProductResolver
from app.modules.dynamic_content.templates import ensure_system_templates
from app.modules.retail.ciss_image_importer import CissProductImageImporter
from app.modules.retail.models import (
    ProductMediaLink,
    RetailOfferCampaign,
    RetailOfferItem,
    RetailProduct,
    RetailStoreProduct,
)
from app.modules.retail.offer_price import OfferPriceResolver
from app.modules.retail.product_media_service import ProductMediaService
from app.modules.retail.providers.mock import MockRetailDataProvider
from app.modules.retail.sync_service import RetailSyncService
from app.modules.signage.models import MediaAsset
from app.modules.signage.storage import checksum


def test_offer_price_direct_and_weight():
    direct = OfferPriceResolver.resolve(val_preco="9.99", flag_preco_mandatorio="F")
    assert direct.calculation_type == "DIRECT"
    assert direct.effective_offer_price == Decimal("9.99")

    weight = OfferPriceResolver.resolve(
        val_preco="12.50", flag_preco_mandatorio="T", val_grama_entrada="0.5"
    )
    assert weight.calculation_type == "WEIGHT_CONVERTED"
    assert weight.effective_offer_price == Decimal("6.25")

    bad = OfferPriceResolver.resolve(val_preco="10", flag_preco_mandatorio="T", val_grama_entrada=None)
    assert bad.calculation_type == "INVALID"
    assert bad.effective_offer_price is None


def test_manual_image_precedes_ciss(seeded):
    db = seeded["db"]
    store_id = seeded["store"].id
    svc = RetailSyncService(db, provider=MockRetailDataProvider())
    svc.upsert_store_source(store_id, company_code="1")
    svc.sync_store(store_id, entities=["PRODUCT", "AVAILABILITY"], full=True, skip_invalidation=True)
    product = db.scalars(select(RetailProduct)).first()
    assert product

    manual_asset = MediaAsset(
        store_id=store_id,
        name="manual",
        media_type="IMAGE",
        mime_type="image/png",
        public_url="/media/files/manual.png",
        checksum="a" * 64,
        active=True,
    )
    ciss_asset = MediaAsset(
        store_id=store_id,
        name="ciss",
        media_type="IMAGE",
        mime_type="image/jpeg",
        public_url="/media/files/ciss.jpg",
        checksum="b" * 64,
        active=True,
    )
    db.add_all([manual_asset, ciss_asset])
    db.flush()
    db.add_all(
        [
            ProductMediaLink(
                product_id=product.id,
                store_id=store_id,
                media_asset_id=ciss_asset.id,
                purpose="PRIMARY",
                source="CISS",
                is_primary=True,
                active=True,
            ),
            ProductMediaLink(
                product_id=product.id,
                store_id=store_id,
                media_asset_id=manual_asset.id,
                purpose="PRIMARY",
                source="MANUAL",
                is_primary=True,
                active=True,
            ),
        ]
    )
    db.commit()

    resolved = ProductMediaService(db).resolve_primary_image(product.id, store_id)
    assert resolved is not None
    assert resolved["asset_id"] == manual_asset.id


def test_ciss_offer_board_selection(seeded):
    db = seeded["db"]
    store_id = seeded["store"].id
    svc = RetailSyncService(db, provider=MockRetailDataProvider())
    svc.upsert_store_source(store_id, company_code="1")
    svc.sync_store(
        store_id,
        entities=["PRODUCT", "PRICE", "PROMOTION", "AVAILABILITY"],
        full=True,
        skip_invalidation=True,
    )
    products = list(db.scalars(select(RetailProduct).where(RetailProduct.active.is_(True))).all())
    assert len(products) >= 2
    p1, p2 = products[0], products[1]

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    campaign = RetailOfferCampaign(
        store_id=store_id,
        source_offer_id="99901",
        name="Oferta QA 5R",
        starts_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=2),
        active=True,
        synced_at=now,
    )
    db.add(campaign)
    db.flush()
    db.add_all(
        [
            RetailOfferItem(
                campaign_id=campaign.id,
                product_id=p1.id,
                offer_price=8.99,
                raw_offer_price=8.99,
                calculation_type="DIRECT",
                active=True,
                synced_at=now,
            ),
            RetailOfferItem(
                campaign_id=campaign.id,
                product_id=p2.id,
                offer_price=3.49,
                raw_offer_price=3.49,
                calculation_type="DIRECT",
                active=True,
                synced_at=now,
            ),
        ]
    )
    db.commit()

    ensure_system_templates(db)
    tpl = db.scalar(select(DynamicContentTemplate).where(DynamicContentTemplate.slug == "promotion_board_2x2"))
    content = DynamicContentService(db).create_content(
        store_id,
        {
            "name": "Board CISS offer",
            "content_type": "PROMOTION_BOARD",
            "selection_mode": "AUTOMATIC",
            "template_id": tpl.id,
            "config": {"items_per_page": 4, "page_duration_seconds": 8},
            "rule": {
                "promotion_only": True,
                "available_only": False,
                "limit_items": 10,
                "sort_mode": "NAME_ASC",
                "config": {"selection_source": "CISS_OFFER", "offer_campaign_id": campaign.id},
            },
        },
    )
    store = seeded["store"]
    from app.modules.dynamic_content.models import DynamicContent

    row = db.get(DynamicContent, content["id"])
    result = DynamicProductResolver(db).resolve(row, store)
    ids = {it.product_id for it in result.items}
    assert p1.id in ids or p2.id in ids
    assert len(result.items) >= 1


def test_image_importer_skips_without_provider_blob(seeded):
    db = seeded["db"]
    store_id = seeded["store"].id
    svc = RetailSyncService(db, provider=MockRetailDataProvider())
    svc.upsert_store_source(store_id, company_code="1")
    svc.sync_store(store_id, entities=["PRODUCT"], full=True, skip_invalidation=True)
    product = db.scalars(select(RetailProduct)).first()
    out = CissProductImageImporter(db, provider=MockRetailDataProvider()).import_for_product(
        product.id, store_id=store_id
    )
    assert out["status"] == "SKIPPED"


def test_entities_include_offer_and_image():
    from app.modules.retail.sync_service import ENTITIES

    assert "OFFER" in ENTITIES
    assert "PRODUCT_IMAGE" in ENTITIES
    assert "PRICE_CHAIN" in ENTITIES

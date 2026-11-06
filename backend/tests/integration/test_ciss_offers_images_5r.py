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


class _FakeImageProvider:
    """Minimal provider for incremental PRODUCT_IMAGE fingerprint skip."""

    PLACEHOLDER_IMAGE_LENGTH = 4912

    def __init__(self, jpeg_bytes: bytes):
        self.jpeg_bytes = jpeg_bytes
        self.blob_calls = 0
        self.meta_calls = 0
        self.fingerprint = f"{len(jpeg_bytes)}:{jpeg_bytes[:32].hex()}"
        self.sha = checksum(jpeg_bytes)

    def fetch_product_image_meta(self, *, source_product_id=None, gtin=None):
        self.meta_calls += 1
        return {
            "usable": True,
            "idcodbarprod": gtin or "1",
            "source_product_id": source_product_id,
            "length": len(self.jpeg_bytes),
            "head_hex": self.jpeg_bytes[:32].hex(),
            "fingerprint": self.fingerprint,
        }

    def fetch_product_image_blob(self, *, source_product_id=None, gtin=None):
        self.blob_calls += 1
        return {
            "idcodbarprod": gtin or "1",
            "source_product_id": source_product_id,
            "bytes": self.jpeg_bytes,
            "sha256": self.sha,
            "length": len(self.jpeg_bytes),
            "format": "JPEG",
            "mime_type": "image/jpeg",
            "fingerprint": self.fingerprint,
        }


def test_image_importer_skips_blob_on_second_sync(seeded, tmp_path, monkeypatch):
    """Second import with same fingerprint must NOT re-read BLOB."""
    from app.core.config import get_settings

    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path))
    get_settings.cache_clear()

    # minimal valid JPEG
    jpeg = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00" + bytes([8] * 64) + b"\xff\xd9"
    )
    provider = _FakeImageProvider(jpeg)

    db = seeded["db"]
    store_id = seeded["store"].id
    svc = RetailSyncService(db, provider=MockRetailDataProvider())
    svc.upsert_store_source(store_id, company_code="1")
    svc.sync_store(store_id, entities=["PRODUCT"], full=True, skip_invalidation=True)
    product = db.scalars(select(RetailProduct)).first()
    assert product

    importer = CissProductImageImporter(db, provider=provider)
    first = importer.import_for_product(product.id, store_id=store_id)
    assert first["status"] == "UPDATED"
    assert first["blob_reads"] == 1
    assert provider.blob_calls == 1

    second = importer.import_for_product(product.id, store_id=store_id)
    assert second["status"] == "UNCHANGED"
    assert second["blob_reads"] == 0
    assert provider.blob_calls == 1  # no additional full BLOB transfer
    assert provider.meta_calls >= 2

    # Import remaining active products once, then second batch must be meta-only
    products = list(db.scalars(select(RetailProduct).where(RetailProduct.active.is_(True))).all())
    for p in products:
        importer.import_for_product(p.id, store_id=store_id)
    blobs_after_fill = provider.blob_calls
    batch = importer.import_store_products(store_id, limit=50)
    assert batch["blob_reads"] == 0
    assert batch["unchanged"] >= 1
    assert provider.blob_calls == blobs_after_fill
    get_settings.cache_clear()


def test_entities_include_offer_and_image():
    from app.modules.retail.sync_service import ENTITIES

    assert "OFFER" in ENTITIES
    assert "PRODUCT_IMAGE" in ENTITIES
    assert "PRICE_CHAIN" in ENTITIES

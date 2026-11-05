from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.exceptions import ValidationError
from app.modules.dynamic_content.content_service import DynamicContentService
from app.modules.dynamic_content.formatters import format_brl, is_displayable_price, to_money
from app.modules.dynamic_content.models import DynamicContentTemplate
from app.modules.dynamic_content.price_resolver import PriceDisplayResolver
from app.modules.dynamic_content.templates import ensure_system_templates
from app.modules.org.models.entities import Store
from app.modules.retail.models import RetailPrice, RetailProduct, RetailPromotion, RetailStoreProduct, RetailSyncWatermark
from app.modules.retail.providers.mock import MockRetailDataProvider
from app.modules.retail.sync_service import RetailSyncService


def _seed_retail(db, store_id: str):
    svc = RetailSyncService(db, provider=MockRetailDataProvider())
    svc.upsert_store_source(store_id, company_code="1")
    svc.sync_store(store_id, entities=["PRODUCT", "PRICE", "PROMOTION", "AVAILABILITY"], full=True)
    # force PRICE watermark fresh
    for entity in ("PRODUCT", "PRICE", "PROMOTION", "AVAILABILITY"):
        wm = db.scalar(
            select(RetailSyncWatermark).where(
                RetailSyncWatermark.store_id == store_id, RetailSyncWatermark.entity == entity
            )
        )
        if wm:
            wm.last_success_at = datetime.now(timezone.utc).replace(tzinfo=None)
            wm.last_error_at = None
    db.commit()


def test_formatters_and_zero_invalid():
    assert format_brl(54.9) == "R$ 54,90"
    assert format_brl("1234.5") == "R$ 1.234,50"
    assert is_displayable_price(0) is False
    assert is_displayable_price(-1) is False
    assert to_money("3.99") == to_money(3.99)


def test_system_templates_seed_idempotent(seeded):
    db = seeded["db"]
    ensure_system_templates(db)
    ensure_system_templates(db)
    rows = list(
        db.scalars(
            select(DynamicContentTemplate).where(
                DynamicContentTemplate.store_id.is_(None),
                DynamicContentTemplate.is_system.is_(True),
            )
        ).all()
    )
    assert len(rows) == 4
    slugs = {r.slug for r in rows}
    assert slugs == {
        "price_table_clean",
        "price_table_compact",
        "price_table_two_columns",
        "price_table_promo",
    }


def test_manual_automatic_hybrid_and_isolation(seeded, client, auth_header):
    db = seeded["db"]
    store_id = seeded["store"].id
    _seed_retail(db, store_id)
    svc = DynamicContentService(db)
    templates = svc.list_templates()
    clean = next(t for t in templates if t["slug"] == "price_table_clean")

    products = list(db.scalars(select(RetailProduct)).all())
    picanha = next(p for p in products if p.source_product_id == "1001:0")
    banana = next(p for p in products if p.source_product_id == "2001:0")
    alcatra = next(p for p in products if p.source_product_id == "1002:0")

    manual = svc.create_content(
        store_id,
        {
            "name": "Açougue manual",
            "selection_mode": "MANUAL",
            "template_id": clean["id"],
            "config": {"items_per_page": 8, "page_duration_seconds": 8, "duration_mode": "FULL_CYCLE", "title": "Açougue"},
            "products": [
                {"product_id": banana.id, "position": 0},
                {"product_id": picanha.id, "position": 1},
            ],
        },
    )
    assert manual["selection_mode"] == "MANUAL"
    prev = svc.preview(manual["id"], store_id)
    assert prev["status"] == "PRONTA"
    assert prev["item_count"] >= 2
    # manual order: banana then picanha
    ids = [i["product_id"] for i in prev["pages"][0]["items"]]
    assert ids[0] == banana.id
    assert ids[1] == picanha.id

    # regular / promo / unit
    pico = next(i for i in prev["pages"][0]["items"] if i["product_id"] == picanha.id)
    assert pico["unit"] == "KG"
    assert pico["is_promotion"] is True
    assert pico["show_from_to"] is True
    assert pico["display_price"] == 54.9
    assert pico["regular_price"] == 69.9

    # quantity tiers on banana
    ban = next(i for i in prev["pages"][0]["items"] if i["product_id"] == banana.id)
    assert len(ban["quantity_tiers"]) >= 2
    assert "ou mais" in ban["quantity_tiers"][0]["condition_text"].lower() or ban["quantity_tiers"][0]["min_qty"] == 3

    auto = svc.create_content(
        store_id,
        {
            "name": "Auto açougue",
            "selection_mode": "AUTOMATIC",
            "template_id": clean["id"],
            "config": {"items_per_page": 8, "page_duration_seconds": 5, "duration_mode": "FULL_CYCLE"},
            "rule": {"section_code": "1", "limit_items": 10, "sort_mode": "NAME_ASC", "available_only": False},
        },
    )
    auto_prev = svc.preview(auto["id"], store_id)
    assert auto_prev["item_count"] >= 1

    hybrid = svc.create_content(
        store_id,
        {
            "name": "Hybrid",
            "selection_mode": "HYBRID",
            "template_id": clean["id"],
            "config": {"items_per_page": 8, "page_duration_seconds": 8, "duration_mode": "FULL_CYCLE"},
            "rule": {"section_code": "1", "limit_items": 5, "sort_mode": "NAME_ASC"},
            "products": [
                {"product_id": banana.id, "pinned": True, "position": 0},
                {"product_id": alcatra.id, "excluded": True},
            ],
        },
    )
    hy = svc.preview(hybrid["id"], store_id)
    hy_ids = [i["product_id"] for page in hy["pages"] for i in page["items"]]
    assert hy_ids[0] == banana.id
    assert alcatra.id not in hy_ids

    # available_only rejected
    with pytest.raises(ValidationError):
        svc.create_content(
            store_id,
            {
                "name": "bad",
                "selection_mode": "AUTOMATIC",
                "template_id": clean["id"],
                "config": {"items_per_page": 8, "page_duration_seconds": 8},
                "rule": {"available_only": True, "limit_items": 5},
            },
        )

    # store isolation
    other = Store(company_id=seeded["company"].id, name="Outra", timezone="America/Cuiaba")
    db.add(other)
    db.commit()
    db.refresh(other)
    with pytest.raises(Exception):
        svc.get_content(manual["id"], other.id)

    # soft delete
    svc.soft_delete(manual["id"], store_id)
    listed = svc.list_contents(store_id)
    assert all(c["id"] != manual["id"] for c in listed)

    # API smoke
    r = client.get(f"/api/v1/dynamic-content/templates?store_id={store_id}", headers=auth_header)
    assert r.status_code == 200
    assert len(r.json()) >= 4


def test_promo_expired_and_hash_stability(seeded):
    db = seeded["db"]
    store = seeded["store"]
    store.timezone = "America/Cuiaba"
    db.commit()
    _seed_retail(db, store.id)
    svc = DynamicContentService(db)
    clean = next(t for t in svc.list_templates() if t["slug"] == "price_table_clean")
    products = list(db.scalars(select(RetailProduct)).all())
    alcatra = next(p for p in products if p.source_product_id == "1002:0")
    # expired promo fixture from mock — should not be active display
    display = PriceDisplayResolver(db).resolve_product(store, alcatra)
    assert display.is_promotion is False
    assert display.display_price == to_money(49.9)

    content = svc.create_content(
        store.id,
        {
            "name": "Hash test",
            "selection_mode": "MANUAL",
            "template_id": clean["id"],
            "config": {"items_per_page": 8, "page_duration_seconds": 8, "duration_mode": "FULL_CYCLE"},
            "products": [{"product_id": alcatra.id, "position": 0}],
        },
    )
    a = svc.preview(content["id"], store.id)
    b = svc.preview(content["id"], store.id)
    assert a["content_hash"] == b["content_hash"]

    # change price → hash changes
    regular = db.scalar(
        select(RetailPrice).where(
            RetailPrice.store_id == store.id,
            RetailPrice.product_id == alcatra.id,
            RetailPrice.price_kind == "REGULAR",
            RetailPrice.active.is_(True),
        )
    )
    regular.amount = 59.9
    db.commit()
    c = svc.preview(content["id"], store.id)
    assert c["content_hash"] != a["content_hash"]


def test_pagination_durations_and_stale_block(seeded):
    db = seeded["db"]
    store_id = seeded["store"].id
    _seed_retail(db, store_id)
    svc = DynamicContentService(db)
    clean = next(t for t in svc.list_templates() if t["slug"] == "price_table_clean")
    products = [p for p in db.scalars(select(RetailProduct)).all() if p.active][:3]
    # clean template min items_per_page = 4; use 4 with 3 items → 1 page, still validates FULL_CYCLE math
    content = svc.create_content(
        store_id,
        {
            "name": "Pages",
            "selection_mode": "MANUAL",
            "template_id": clean["id"],
            "config": {
                "items_per_page": 4,
                "page_duration_seconds": 8,
                "duration_mode": "FULL_CYCLE",
            },
            "products": [{"product_id": p.id, "position": i} for i, p in enumerate(products)],
        },
    )
    prev = svc.preview(content["id"], store_id)
    assert prev["item_count"] >= 1
    assert prev["pagination"]["page_count"] >= 1
    assert prev["pagination"]["total_duration_seconds"] == prev["pagination"]["page_count"] * 8

    # FIXED
    svc.update_content(
        content["id"],
        store_id,
        {
            "config": {
                "items_per_page": 4,
                "page_duration_seconds": 8,
                "duration_mode": "FIXED",
                "total_duration_seconds": 30,
            }
        },
    )
    fixed = svc.preview(content["id"], store_id)
    assert fixed["pagination"]["duration_mode"] == "FIXED"
    assert fixed["pagination"]["total_duration_seconds"] == 30

    # STALE block
    wm = db.scalar(
        select(RetailSyncWatermark).where(RetailSyncWatermark.store_id == store_id, RetailSyncWatermark.entity == "PRICE")
    )
    wm.last_success_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=2000)
    db.commit()
    with pytest.raises(ValidationError):
        svc.preview(content["id"], store_id)


def test_missing_price_manual_warning(seeded):
    db = seeded["db"]
    store_id = seeded["store"].id
    _seed_retail(db, store_id)
    # create product without price
    orphan = RetailProduct(source_system="CISS", source_product_id="9999:0", description="SEM PRECO", unit="UN", active=True)
    db.add(orphan)
    db.flush()
    db.add(
        RetailStoreProduct(
            store_id=store_id, product_id=orphan.id, source_company_code="1", sellable=True, available=True
        )
    )
    db.commit()

    svc = DynamicContentService(db)
    clean = next(t for t in svc.list_templates() if t["slug"] == "price_table_clean")
    # refresh watermarks fresh
    for entity in ("PRICE",):
        wm = db.scalar(
            select(RetailSyncWatermark).where(RetailSyncWatermark.store_id == store_id, RetailSyncWatermark.entity == entity)
        )
        if wm:
            wm.last_success_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()

    content = svc.create_content(
        store_id,
        {
            "name": "Missing",
            "selection_mode": "MANUAL",
            "template_id": clean["id"],
            "config": {"items_per_page": 8, "page_duration_seconds": 8, "duration_mode": "FULL_CYCLE"},
            "products": [{"product_id": orphan.id, "position": 0}],
        },
    )
    prev = svc.preview(content["id"], store_id)
    assert prev["status"] == "ATENÇÃO"
    assert any("sem preço" in w.lower() for w in prev["warnings"])

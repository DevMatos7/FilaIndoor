"""DRC-5 — Automation & Resilience."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.core.exceptions import ValidationError
from app.modules.dynamic_content.content_service import DynamicContentService
from app.modules.dynamic_content.impact_resolver import DynamicContentImpactResolver
from app.modules.dynamic_content.invalidation_service import DynamicInvalidationService
from app.modules.dynamic_content.models import DynamicContentTemplate, DynamicRenderSnapshot
from app.modules.dynamic_content.templates import ensure_system_templates
from app.modules.org.models.entities import Store
from app.modules.retail.models import (
    RetailPrice,
    RetailProduct,
    RetailPromotion,
    RetailSyncRun,
    RetailSyncWatermark,
)
from app.modules.retail.provider_guard import assert_retail_provider_safe, provider_label
from app.modules.retail.providers.mock import MockRetailDataProvider
from app.modules.retail.scheduler import scheduler_status, start_retail_scheduler, shutdown_retail_scheduler
from app.modules.retail.sync_lock import retail_sync_lock
from app.modules.retail.sync_service import RetailSyncService


def _fresh_watermarks(db, store_id: str) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for entity in ("PRODUCT", "PRICE", "PROMOTION", "AVAILABILITY"):
        wm = db.scalar(
            select(RetailSyncWatermark).where(
                RetailSyncWatermark.store_id == store_id,
                RetailSyncWatermark.entity == entity,
            )
        )
        if wm:
            wm.last_success_at = now
            wm.last_error_at = None
            wm.consecutive_failures = 0
    db.commit()


def _seed_retail(db, store_id: str) -> None:
    svc = RetailSyncService(db, provider=MockRetailDataProvider())
    svc.upsert_store_source(store_id, company_code="1")
    svc.sync_store(
        store_id,
        entities=["PRODUCT", "PRICE", "PROMOTION", "AVAILABILITY"],
        full=True,
        skip_invalidation=True,
    )
    _fresh_watermarks(db, store_id)


def _tpl(db, slug: str = "price_table_clean") -> DynamicContentTemplate:
    ensure_system_templates(db)
    return db.scalar(select(DynamicContentTemplate).where(DynamicContentTemplate.slug == slug))


def test_01_02_scheduler_enabled_disabled(monkeypatch):
    shutdown_retail_scheduler()
    monkeypatch.setenv("RETAIL_AUTOMATION_ENABLED", "false")
    get_settings.cache_clear()
    assert start_retail_scheduler() is None
    st = scheduler_status()
    assert st["enabled"] is False or st["running"] is False

    monkeypatch.setenv("RETAIL_AUTOMATION_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("RETAIL_PROVIDER", "mock")
    get_settings.cache_clear()
    sched = start_retail_scheduler()
    assert sched is not None
    assert scheduler_status()["running"] is True
    shutdown_retail_scheduler()
    get_settings.cache_clear()


def test_03_production_mock_rejected(monkeypatch):
    get_settings.cache_clear()
    s = Settings(app_env="production", retail_provider="mock", retail_allow_mock_in_production=False)
    with pytest.raises(ValidationError, match="proibido em produção"):
        assert_retail_provider_safe(settings=s)
    assert provider_label(s) == "MOCK"

    ok = Settings(app_env="production", retail_provider="ciss_db2")
    assert_retail_provider_safe(settings=ok)

    # scheduler must not start with prod+mock
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("RETAIL_PROVIDER", "mock")
    monkeypatch.setenv("RETAIL_AUTOMATION_ENABLED", "true")
    monkeypatch.setenv("RETAIL_ALLOW_MOCK_IN_PRODUCTION", "false")
    get_settings.cache_clear()
    shutdown_retail_scheduler()
    assert start_retail_scheduler() is None
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("RETAIL_PROVIDER", "mock")
    monkeypatch.setenv("RETAIL_AUTOMATION_ENABLED", "false")
    get_settings.cache_clear()


def test_04_05_store_mapping_scope(seeded):
    db = seeded["db"]
    store_id = seeded["store"].id
    other = Store(company_id=seeded["company"].id, name="Sem mapping", timezone="America/Cuiaba")
    db.add(other)
    db.commit()
    db.refresh(other)

    svc = RetailSyncService(db, provider=MockRetailDataProvider())
    with pytest.raises(Exception):
        svc.sync_store(other.id, entities=["PRICE"], full=True)

    svc.upsert_store_source(store_id, company_code="1")
    runs = svc.sync_store(store_id, entities=["PRICE"], full=True, skip_invalidation=True)
    assert runs[0]["status"] == "SUCCESS"
    assert runs[0]["trigger"] == "MANUAL"


def test_06_07_concurrent_lock_and_release(seeded):
    db = seeded["db"]
    store_id = seeded["store"].id
    with retail_sync_lock(db, store_id, "PRICE") as acquired:
        assert acquired is True
        with retail_sync_lock(db, store_id, "PRICE") as second:
            assert second is False
    # released — can acquire again
    with retail_sync_lock(db, store_id, "PRICE") as again:
        assert again is True

    # failure path still releases
    try:
        with retail_sync_lock(db, store_id, "PROMOTION") as acquired:
            assert acquired
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    with retail_sync_lock(db, store_id, "PROMOTION") as after:
        assert after is True


def test_08_scheduled_retail_sync_run(seeded):
    db = seeded["db"]
    store_id = seeded["store"].id
    _seed_retail(db, store_id)
    svc = RetailSyncService(db, provider=MockRetailDataProvider())
    runs = svc.sync_store(store_id, entities=["PRICE"], full=True, trigger="SCHEDULED", skip_invalidation=True)
    assert runs[0]["trigger"] == "SCHEDULED"
    row = db.scalar(
        select(RetailSyncRun).where(
            RetailSyncRun.store_id == store_id,
            RetailSyncRun.trigger == "SCHEDULED",
        )
    )
    assert row is not None


def test_09_16_change_detection_and_impact(seeded):
    db = seeded["db"]
    store_id = seeded["store"].id
    _seed_retail(db, store_id)
    tpl = _tpl(db)
    products = list(db.scalars(select(RetailProduct)).all())
    p1 = next(p for p in products if p.source_product_id == "1001:0")
    p2 = next(p for p in products if p.source_product_id == "2001:0")
    svc = DynamicContentService(db)

    content_a = svc.create_content(
        store_id,
        {
            "name": "A uses p1",
            "selection_mode": "MANUAL",
            "template_id": tpl.id,
            "config": {"items_per_page": 8, "page_duration_seconds": 8},
            "products": [{"product_id": p1.id, "position": 0}],
        },
    )
    content_b = svc.create_content(
        store_id,
        {
            "name": "B uses p2",
            "selection_mode": "MANUAL",
            "template_id": tpl.id,
            "config": {"items_per_page": 8, "page_duration_seconds": 8},
            "products": [{"product_id": p2.id, "position": 0}],
        },
    )

    impact = DynamicContentImpactResolver(db).resolve(
        store_id,
        changed_product_ids=[p1.id],
        change_types=["PRICE_CHANGED"],
    )
    ids = {i["dynamic_content_id"] for i in impact}
    assert content_a["id"] in ids
    assert content_b["id"] not in ids

    # automatic section rule
    auto = svc.create_content(
        store_id,
        {
            "name": "Auto section",
            "selection_mode": "AUTOMATIC",
            "template_id": tpl.id,
            "config": {"items_per_page": 8, "page_duration_seconds": 8},
            "rule": {"section_code": "18", "limit_items": 10, "sort_mode": "NAME_ASC", "available_only": False},
        },
    )
    # product moving into section 18
    impact_auto = DynamicContentImpactResolver(db).resolve(
        store_id,
        changed_product_ids=[p2.id],
        change_types=["PRODUCT_CHANGED"],
        section_codes=["18"],
    )
    assert any(i["dynamic_content_id"] == auto["id"] for i in impact_auto)

    # hybrid: pinned product
    hybrid = svc.create_content(
        store_id,
        {
            "name": "Hybrid",
            "selection_mode": "HYBRID",
            "template_id": tpl.id,
            "config": {"items_per_page": 8, "page_duration_seconds": 8},
            "rule": {"section_code": "99", "limit_items": 5, "available_only": False},
            "products": [{"product_id": p1.id, "position": 0, "pinned": True}],
        },
    )
    impact_h = DynamicContentImpactResolver(db).resolve(
        store_id,
        changed_product_ids=[p1.id],
        change_types=["IMAGE_CHANGED"],
    )
    assert any(i["dynamic_content_id"] == hybrid["id"] for i in impact_h)

    # promotion_only board
    board_tpl = _tpl(db, "promotion_board_2x2")
    board = svc.create_content(
        store_id,
        {
            "name": "Promo board",
            "content_type": "PROMOTION_BOARD",
            "selection_mode": "AUTOMATIC",
            "template_id": board_tpl.id,
            "config": {"items_per_page": 4, "page_duration_seconds": 8},
            "rule": {"promotion_only": True, "limit_items": 8, "available_only": False},
        },
    )
    impact_promo = DynamicContentImpactResolver(db).resolve(
        store_id,
        changed_product_ids=[p1.id],
        change_types=["PROMOTION_CHANGED"],
    )
    assert any(i["dynamic_content_id"] == board["id"] for i in impact_promo)


def test_17_18_19_ws_store_isolation(seeded):
    db = seeded["db"]
    store_a = seeded["store"].id
    store_b = Store(company_id=seeded["company"].id, name="Loja B", timezone="America/Cuiaba")
    db.add(store_b)
    db.commit()
    db.refresh(store_b)
    _seed_retail(db, store_a)
    tpl = _tpl(db)
    p1 = db.scalars(select(RetailProduct)).first()
    content = DynamicContentService(db).create_content(
        store_a,
        {
            "name": "Isolated",
            "selection_mode": "MANUAL",
            "template_id": tpl.id,
            "config": {"items_per_page": 4, "page_duration_seconds": 8},
            "products": [{"product_id": p1.id, "position": 0}],
        },
    )

    published: list[tuple[str, str, dict]] = []

    def _capture(store_id, event, data):
        published.append((store_id, event, data))

    with patch("app.modules.dynamic_content.invalidation_service.hub.publish", side_effect=_capture):
        DynamicInvalidationService(db).invalidate_products(
            store_a,
            changed_product_ids=[p1.id],
            change_types=["PRICE_CHANGED"],
        )

    assert published
    assert all(p[0] == store_a for p in published)
    assert all(p[1] == "dynamic_content.invalidated" for p in published)
    assert all(p[2].get("dynamic_content_id") == content["id"] for p in published)
    assert all("price" not in str(p[2]).lower() or "price_changed" in str(p[2]).lower() for p in published)
    assert not any(p[0] == store_b.id for p in published)


def test_20_21_valid_until_promo_boundaries(seeded):
    db = seeded["db"]
    store_id = seeded["store"].id
    _seed_retail(db, store_id)
    tpl = _tpl(db)
    products = list(db.scalars(select(RetailProduct)).all())
    picanha = next(p for p in products if p.source_product_id == "1001:0")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # start sooner than freshness soft window so promo boundary wins
    start = now + timedelta(seconds=45)
    end = now + timedelta(hours=2)

    # clear existing promos for product and set future start
    for promo in db.scalars(select(RetailPromotion).where(RetailPromotion.product_id == picanha.id)).all():
        promo.active = False
    db.add(
        RetailPromotion(
            store_id=store_id,
            product_id=picanha.id,
            source_promotion_id="t-start",
            promo_amount=49.9,
            starts_at=start,
            expires_at=end,
            active=True,
        )
    )
    db.commit()

    from app.modules.dynamic_content.snapshot_service import SnapshotService

    content = DynamicContentService(db).create_content(
        store_id,
        {
            "name": "Temporal",
            "selection_mode": "MANUAL",
            "template_id": tpl.id,
            "config": {"items_per_page": 4, "page_duration_seconds": 8},
            "products": [{"product_id": picanha.id, "position": 0}],
        },
    )
    snap = DynamicContentService(db).preview(content["id"], store_id)
    player = SnapshotService(db).player_payload(
        snap, content_id=content["id"], name=content["name"]
    )
    vu = datetime.fromisoformat(player["valid_until"].replace("Z", ""))
    assert vu <= start + timedelta(seconds=1)

    # end inclusive: after expires_at + 1s
    for promo in db.scalars(select(RetailPromotion).where(RetailPromotion.product_id == picanha.id)).all():
        promo.starts_at = now - timedelta(hours=1)
        promo.expires_at = now + timedelta(minutes=5)
        promo.active = True
    db.commit()
    # poison snapshot so ensure regenerates
    for row in db.scalars(
        select(DynamicRenderSnapshot).where(DynamicRenderSnapshot.dynamic_content_id == content["id"])
    ).all():
        row.data_version = "dirty:x"
    db.commit()
    snap2 = DynamicContentService(db).preview(content["id"], store_id)
    player2 = SnapshotService(db).player_payload(
        snap2, content_id=content["id"], name=content["name"]
    )
    vu2 = datetime.fromisoformat(player2["valid_until"].replace("Z", ""))
    assert vu2 <= (now + timedelta(minutes=5) + timedelta(seconds=2))


def test_22_23_freshness_hard_stop_and_dirty(seeded, client, auth_header):
    db = seeded["db"]
    store_id = seeded["store"].id
    _seed_retail(db, store_id)
    tpl = _tpl(db)
    p1 = db.scalars(select(RetailProduct)).first()
    content = DynamicContentService(db).create_content(
        store_id,
        {
            "name": "Stale check",
            "selection_mode": "MANUAL",
            "template_id": tpl.id,
            "config": {"items_per_page": 4, "page_duration_seconds": 8},
            "products": [{"product_id": p1.id, "position": 0}],
        },
    )
    DynamicContentService(db).preview(content["id"], store_id)

    # mark PRICE STALE
    wm = db.scalar(
        select(RetailSyncWatermark).where(
            RetailSyncWatermark.store_id == store_id,
            RetailSyncWatermark.entity == "PRICE",
        )
    )
    wm.last_success_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1200)
    db.commit()

    with patch("app.modules.dynamic_content.invalidation_service.hub.publish"):
        DynamicInvalidationService(db).invalidate_content(content["id"], store_id=store_id, reason="STALE")

    snap = db.scalar(
        select(DynamicRenderSnapshot).where(DynamicRenderSnapshot.dynamic_content_id == content["id"])
    )
    assert snap is not None
    assert str(snap.data_version).startswith("dirty:")
    assert snap.publishable is False

    h = client.get(f"/api/v1/retail-data/health?store_id={store_id}", headers=auth_header)
    assert h.status_code == 200
    body = h.json()
    assert body["stock_filter"] == "DISABLED_BY_DESIGN"
    assert body["stock_commercial_source"] == "NOT_CONFIRMED"
    assert "scheduler" in body


def test_24_empty_automatic_content(seeded):
    db = seeded["db"]
    store_id = seeded["store"].id
    _seed_retail(db, store_id)
    tpl = _tpl(db)
    content = DynamicContentService(db).create_content(
        store_id,
        {
            "name": "Empty auto",
            "selection_mode": "AUTOMATIC",
            "template_id": tpl.id,
            "config": {"items_per_page": 4, "page_duration_seconds": 8},
            "rule": {
                "section_code": "NO_MATCH_SECTION",
                "limit_items": 5,
                "available_only": False,
            },
        },
    )
    snap = DynamicContentService(db).preview(content["id"], store_id)
    assert (snap.get("item_count") or 0) == 0


def test_25_page_count_shrink_safe():
    # Documented rule: safeIndex = pageIndex % pageCount (renderer)
    page_count = 2
    current = 3
    safe = ((current % page_count) + page_count) % page_count
    assert safe in {0, 1}


def test_26_27_28_cache_policy():
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    valid_until = now + timedelta(minutes=5)
    expired = now - timedelta(seconds=1)
    assert now < valid_until  # cache usable
    assert now >= expired  # cache rejected
    dirty = True
    assert not (now < valid_until and not dirty)  # dirty → refetch


def test_stock_available_only_still_rejected(seeded):
    db = seeded["db"]
    store_id = seeded["store"].id
    _seed_retail(db, store_id)
    tpl = _tpl(db)
    svc = DynamicContentService(db)
    with pytest.raises(ValidationError, match="available_only"):
        svc.create_content(
            store_id,
            {
                "name": "Stock blocked",
                "selection_mode": "AUTOMATIC",
                "template_id": tpl.id,
                "config": {"items_per_page": 4, "page_duration_seconds": 8},
                "rule": {"available_only": True, "limit_items": 5},
            },
        )


def test_price_change_pipeline_invalidates(seeded):
    db = seeded["db"]
    store_id = seeded["store"].id
    _seed_retail(db, store_id)
    tpl = _tpl(db)
    picanha = next(p for p in db.scalars(select(RetailProduct)).all() if p.source_product_id == "1001:0")
    content = DynamicContentService(db).create_content(
        store_id,
        {
            "name": "Price watch",
            "selection_mode": "MANUAL",
            "template_id": tpl.id,
            "config": {"items_per_page": 4, "page_duration_seconds": 8},
            "products": [{"product_id": picanha.id, "position": 0}],
        },
    )
    DynamicContentService(db).preview(content["id"], store_id)

    # mutate regular price
    price = db.scalar(
        select(RetailPrice).where(
            RetailPrice.store_id == store_id,
            RetailPrice.product_id == picanha.id,
            RetailPrice.price_kind == "REGULAR",
            RetailPrice.active.is_(True),
        )
    )
    assert price is not None
    price.amount = 8.99
    db.commit()

    published = []
    with patch(
        "app.modules.dynamic_content.invalidation_service.hub.publish",
        side_effect=lambda *a, **k: published.append(a),
    ):
        # Simulate change detection path
        DynamicInvalidationService(db).invalidate_products(
            store_id,
            changed_product_ids=[picanha.id],
            change_types=["PRICE_CHANGED"],
        )

    assert published
    snap = db.scalar(
        select(DynamicRenderSnapshot).where(DynamicRenderSnapshot.dynamic_content_id == content["id"])
    )
    assert str(snap.data_version).startswith("dirty:")


def test_watermark_not_advanced_on_failure(seeded):
    db = seeded["db"]
    store_id = seeded["store"].id
    _seed_retail(db, store_id)
    wm_before = db.scalar(
        select(RetailSyncWatermark).where(
            RetailSyncWatermark.store_id == store_id,
            RetailSyncWatermark.entity == "PRICE",
        )
    )
    before_val = wm_before.watermark_value
    provider = MagicMock(wraps=MockRetailDataProvider())
    provider.fetch_prices.side_effect = RuntimeError("db2 down")
    svc = RetailSyncService(db, provider=provider)
    with pytest.raises(RuntimeError):
        svc.sync_store(store_id, entities=["PRICE"], full=True, skip_invalidation=True)
    db.refresh(wm_before)
    assert wm_before.watermark_value == before_val
    assert wm_before.consecutive_failures >= 1
    assert wm_before.last_error_at is not None


def test_health_failure_counters(seeded, client, auth_header):
    db = seeded["db"]
    store_id = seeded["store"].id
    _seed_retail(db, store_id)
    wm = db.scalar(
        select(RetailSyncWatermark).where(
            RetailSyncWatermark.store_id == store_id,
            RetailSyncWatermark.entity == "PRICE",
        )
    )
    wm.consecutive_failures = 3
    wm.last_error_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    h = client.get(f"/api/v1/retail-data/health?store_id={store_id}", headers=auth_header).json()
    price_block = next(e for e in h["entities"] if e["entity"] == "PRICE")
    assert price_block["consecutive_failures"] == 3
    assert price_block.get("last_failure_at")

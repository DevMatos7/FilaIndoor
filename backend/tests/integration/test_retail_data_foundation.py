from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.exceptions import ValidationError
from app.modules.retail.freshness import FreshnessStatus, classify_freshness
from app.modules.retail.models import RetailPrice, RetailProduct, RetailPromotion, RetailStoreProduct
from app.modules.retail.providers.mock import MockRetailDataProvider
from app.modules.retail.reconcile_service import RetailReconciliationService
from app.modules.retail.sync_service import RetailSyncService
from app.modules.retail.timezone_util import validate_iana_timezone


def test_timezone_valid_and_invalid():
    assert validate_iana_timezone("America/Sao_Paulo") == "America/Sao_Paulo"
    with pytest.raises(ValidationError):
        validate_iana_timezone("Not/AZone")


def test_freshness_bands():
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    assert classify_freshness(now - timedelta(seconds=10)) == FreshnessStatus.FRESH
    assert classify_freshness(now - timedelta(seconds=400)) == FreshnessStatus.DEGRADED
    assert classify_freshness(now - timedelta(seconds=1000)) == FreshnessStatus.STALE
    assert classify_freshness(None) == FreshnessStatus.UNKNOWN
    assert classify_freshness(None, failed=True) == FreshnessStatus.FAILED


def test_store_mapping_and_sync_idempotent(seeded, client, auth_header):
    store_id = seeded["store"].id
    db = seeded["db"]
    svc = RetailSyncService(db, provider=MockRetailDataProvider())

    mapping = svc.upsert_store_source(store_id, company_code="1")
    assert mapping["company_code"] == "1"

    runs1 = svc.sync_store(store_id, entities=["PRODUCT", "PRICE", "PROMOTION", "AVAILABILITY"], full=True)
    assert all(r["status"] == "SUCCESS" for r in runs1)
    products_n = db.scalars(select(RetailProduct)).all()
    assert len(products_n) >= 3
    prices_n = db.scalars(select(RetailPrice).where(RetailPrice.store_id == store_id, RetailPrice.active.is_(True))).all()
    assert any(p.price_kind == "REGULAR" for p in prices_n)
    assert any(p.price_kind == "PROMOTION" for p in prices_n)
    assert any(p.price_kind == "QUANTITY" for p in prices_n)
    promos = db.scalars(select(RetailPromotion).where(RetailPromotion.store_id == store_id)).all()
    assert any(p.active for p in promos)
    assert any(not p.active for p in promos)  # expired kept inactive

    # inactive product present
    assert any(not p.active for p in products_n)

    # unit preserved
    picanha = next(p for p in products_n if p.source_product_id == "1001:0")
    assert picanha.unit == "KG"

    count_before = len(products_n)
    runs2 = svc.sync_store(store_id, entities=["PRODUCT", "PRICE"], full=True)
    assert all(r["status"] == "SUCCESS" for r in runs2)
    products_after = db.scalars(select(RetailProduct)).all()
    assert len(products_after) == count_before  # no duplication

    # watermark advanced
    assert runs1[0]["watermark_after"] or runs1[1]["watermark_after"]

    # health API
    h = client.get(f"/api/v1/retail-data/health?store_id={store_id}", headers=auth_header)
    assert h.status_code == 200
    body = h.json()
    assert body["source"] == "CISS"
    assert "password" not in str(body).lower()
    assert "dsn" not in str(body).lower()
    assert body["mapping"]["configured"] is True

    # cross-store isolation: other store has no prices
    from app.modules.org.models.entities import Store

    other = Store(company_id=seeded["company"].id, name="Outra Loja", timezone="America/Sao_Paulo")
    db.add(other)
    db.commit()
    db.refresh(other)
    other_prices = db.scalars(select(RetailPrice).where(RetailPrice.store_id == other.id)).all()
    assert other_prices == []

    # reconciliation MATCH for picanha
    rec = RetailReconciliationService(db, provider=MockRetailDataProvider()).reconcile(store_id, [picanha.id])
    assert rec["summary"]["mismatch"] == 0
    assert rec["results"][0]["status"] in {"MATCH", "NOT_COMPARABLE"}

    # force mismatch
    picanha.description = "WRONG"
    db.commit()
    rec2 = RetailReconciliationService(db, provider=MockRetailDataProvider()).reconcile(store_id, [picanha.id])
    assert rec2["summary"]["mismatch"] >= 1

    # zero ≠ missing: product without local availability field treated carefully
    missing = RetailReconciliationService(db, provider=MockRetailDataProvider()).reconcile(
        store_id, ["00000000-0000-0000-0000-000000000000"]
    )
    assert missing["results"][0]["status"] == "NOT_COMPARABLE"


def test_sync_run_api_and_manual_sync(seeded, client, auth_header):
    store_id = seeded["store"].id
    r = client.post(
        "/api/v1/retail-data/store-sources",
        headers=auth_header,
        json={"store_id": store_id, "company_code": "1"},
    )
    assert r.status_code == 200

    # Force mock provider via env is default retail_provider=mock
    sync = client.post(
        "/api/v1/retail-data/sync",
        headers=auth_header,
        json={"store_id": store_id, "entities": ["PRODUCT", "PRICE"], "full": True},
    )
    assert sync.status_code == 200
    runs = client.get(f"/api/v1/retail-data/sync-runs?store_id={store_id}", headers=auth_header)
    assert runs.status_code == 200
    assert len(runs.json()) >= 1

    products = client.get("/api/v1/retail-products?limit=20", headers=auth_header)
    assert products.status_code == 200
    assert len(products.json()) >= 1


def test_quantity_pricing_condition(seeded):
    db = seeded["db"]
    store_id = seeded["store"].id
    svc = RetailSyncService(db, provider=MockRetailDataProvider())
    svc.upsert_store_source(store_id, company_code="1")
    svc.sync_store(store_id, entities=["PRODUCT", "PRICE"], full=True)
    qty = db.scalars(
        select(RetailPrice).where(
            RetailPrice.store_id == store_id,
            RetailPrice.price_kind == "QUANTITY",
            RetailPrice.active.is_(True),
        )
    ).all()
    assert len(qty) >= 2
    assert all(p.min_qty and p.condition_text for p in qty)


def test_availability_stock(seeded):
    db = seeded["db"]
    store_id = seeded["store"].id
    svc = RetailSyncService(db, provider=MockRetailDataProvider())
    svc.upsert_store_source(store_id, company_code="1")
    svc.sync_store(store_id, entities=["PRODUCT", "AVAILABILITY"], full=True)
    rows = db.scalars(select(RetailStoreProduct).where(RetailStoreProduct.store_id == store_id)).all()
    assert any(r.current_stock_qty and r.current_stock_qty > 0 for r in rows)

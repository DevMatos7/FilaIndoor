"""DRC-4 — Product Visual Engine."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.modules.dynamic_content.content_service import DynamicContentService
from app.modules.dynamic_content.models import DynamicContentTemplate
from app.modules.dynamic_content.templates import ensure_system_templates
from app.modules.queue.models.entities import Display
from app.modules.retail.models import RetailProduct, RetailSyncWatermark
from app.modules.retail.product_media_service import ProductMediaService
from app.modules.retail.providers.mock import MockRetailDataProvider
from app.modules.retail.sync_service import RetailSyncService
from app.modules.signage.models import MediaAsset
from app.modules.signage.storage import media_root

PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


def _seed_retail(db, store_id: str):
    svc = RetailSyncService(db, provider=MockRetailDataProvider())
    svc.upsert_store_source(store_id, company_code="1")
    svc.sync_store(store_id, entities=["PRODUCT", "PRICE", "PROMOTION", "AVAILABILITY"], full=True)
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


def _upload(client, auth_header, store_id: str, name: str):
    files = {"file": (f"{name}.png", PNG_1X1, "image/png")}
    data = {"store_id": store_id, "name": name, "duration_seconds": "5"}
    r = client.post("/api/v1/media", data=data, files=files, headers=auth_header)
    assert r.status_code == 201, r.text
    return r.json()


def test_product_media_primary_and_delete_protection(client, auth_header, seeded, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    from app.core.config import get_settings

    get_settings.cache_clear()
    media_root()

    db = seeded["db"]
    store_id = seeded["store"].id
    _seed_retail(db, store_id)
    prod = db.scalars(select(RetailProduct)).first()
    asset = _upload(client, auth_header, store_id, "Packshot")

    att = client.post(
        f"/api/v1/retail-products/{prod.id}/media",
        json={"media_asset_id": asset["id"], "store_id": store_id, "purpose": "PRIMARY", "is_primary": True},
        headers=auth_header,
    )
    assert att.status_code == 201, att.text
    link_id = att.json()["id"]

    listed = client.get(
        f"/api/v1/retail-products/{prod.id}/media",
        params={"store_id": store_id},
        headers=auth_header,
    )
    assert listed.status_code == 200
    assert len(listed.json()) >= 1

    # delete asset blocked while linked
    blocked = client.delete(f"/api/v1/media/{asset['id']}", params={"store_id": store_id}, headers=auth_header)
    assert blocked.status_code == 409

    # detach link keeps asset
    det = client.delete(
        f"/api/v1/retail-products/{prod.id}/media/{link_id}",
        params={"store_id": store_id},
        headers=auth_header,
    )
    assert det.status_code == 200
    assert db.get(MediaAsset, asset["id"]).active is True


def test_cross_store_media_rejected(client, auth_header, seeded, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    from app.core.config import get_settings
    from app.modules.org.models.entities import Store

    get_settings.cache_clear()
    media_root()
    db = seeded["db"]
    store_a = seeded["store"].id
    store_b = Store(company_id=seeded["company"].id, name="B", timezone="America/Cuiaba")
    db.add(store_b)
    db.commit()
    db.refresh(store_b)
    _seed_retail(db, store_a)
    asset_b = _upload(client, auth_header, store_b.id, "Foreign")
    prod = db.scalars(select(RetailProduct)).first()
    r = client.post(
        f"/api/v1/retail-products/{prod.id}/media",
        json={"media_asset_id": asset_b["id"], "store_id": store_a, "is_primary": True},
        headers=auth_header,
    )
    assert r.status_code in {403, 422}


def test_visual_snapshots_and_hash_with_image(client, auth_header, seeded, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    from app.core.config import get_settings

    get_settings.cache_clear()
    media_root()
    db = seeded["db"]
    store_id = seeded["store"].id
    _seed_retail(db, store_id)
    ensure_system_templates(db)
    products = list(db.scalars(select(RetailProduct)).all())[:4]
    tpl = db.scalar(select(DynamicContentTemplate).where(DynamicContentTemplate.slug == "product_grid_2x2"))
    svc = DynamicContentService(db)
    grid = svc.create_content(
        store_id,
        {
            "name": "Grade QA",
            "selection_mode": "MANUAL",
            "template_id": tpl.id,
            "config": {"page_duration_seconds": 8, "duration_mode": "FULL_CYCLE", "title": "Hortifruti"},
            "products": [{"product_id": p.id, "position": i} for i, p in enumerate(products)],
        },
    )
    snap1 = svc.preview(grid["id"], store_id)
    assert snap1["content_type"] == "PRODUCT_GRID"
    assert snap1["pagination"]["items_per_page"] == 4
    assert snap1["item_count"] >= 1
    h1 = snap1["content_hash"]

    asset = _upload(client, auth_header, store_id, "ImgGrid")
    ProductMediaService(db).attach(
        products[0].id, media_asset_id=asset["id"], store_id=store_id, is_primary=True
    )
    snap2 = svc.preview(grid["id"], store_id)
    assert snap2["content_hash"] != h1
    img = snap2["pages"][0]["items"][0].get("image")
    # first item may not be products[0] depending on order — find one with image
    assert any(i.get("image") for page in snap2["pages"] for i in page["items"])

    hero_tpl = db.scalar(select(DynamicContentTemplate).where(DynamicContentTemplate.slug == "product_hero_clean"))
    hero = svc.create_content(
        store_id,
        {
            "name": "Hero QA",
            "selection_mode": "MANUAL",
            "template_id": hero_tpl.id,
            "config": {"page_duration_seconds": 10, "duration_mode": "FULL_CYCLE"},
            "products": [{"product_id": products[0].id, "position": 0}],
        },
    )
    hs = svc.preview(hero["id"], store_id)
    assert hs["content_type"] == "PRODUCT_HERO"
    assert hs["pagination"]["items_per_page"] == 1

    board_tpl = db.scalar(
        select(DynamicContentTemplate).where(DynamicContentTemplate.slug == "promotion_board_2x2")
    )
    board = svc.create_content(
        store_id,
        {
            "name": "Board QA",
            "selection_mode": "AUTOMATIC",
            "template_id": board_tpl.id,
            "config": {"page_duration_seconds": 8, "duration_mode": "FULL_CYCLE"},
            "rule": {"promotion_only": True, "limit_items": 8, "sort_mode": "NAME_ASC"},
        },
    )
    bs = svc.preview(board["id"], store_id)
    assert bs["content_type"] == "PROMOTION_BOARD"


def test_player_visual_payload_and_list_batch(client, auth_header, seeded, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    from app.core.config import get_settings

    get_settings.cache_clear()
    media_root()
    db = seeded["db"]
    store_id = seeded["store"].id
    _seed_retail(db, store_id)
    ensure_system_templates(db)
    products = list(db.scalars(select(RetailProduct)).all())[:4]
    tpl = db.scalar(select(DynamicContentTemplate).where(DynamicContentTemplate.slug == "product_grid_2x2"))
    svc = DynamicContentService(db)
    grid = svc.create_content(
        store_id,
        {
            "name": "TV Grid",
            "selection_mode": "MANUAL",
            "template_id": tpl.id,
            "config": {"page_duration_seconds": 8, "duration_mode": "FULL_CYCLE"},
            "products": [{"product_id": p.id, "position": i} for i, p in enumerate(products)],
        },
    )
    svc.preview(grid["id"], store_id)

    display = Display(
        store_id=store_id,
        department_id=seeded["department"].id,
        queue_id=seeded["queue"].id,
        name="TV V",
        code="TV-V",
        token="display-visual-token",
        audio_enabled=False,
    )
    db.add(display)
    db.commit()

    r = client.get(
        f"/api/v1/player/dynamic-content/{grid['id']}",
        headers={"X-Display-Token": "display-visual-token"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["type"] == "PRODUCT_GRID"
    assert "pages" in body

    lst = client.get(
        "/api/v1/retail-products",
        params={"store_id": store_id, "limit": 20, "has_image": "all"},
        headers=auth_header,
    )
    assert lst.status_code == 200
    assert "image_status" in lst.json()[0]


def test_system_visual_templates(seeded):
    db = seeded["db"]
    ensure_system_templates(db)
    ensure_system_templates(db)
    slugs = {
        r.slug
        for r in db.scalars(
            select(DynamicContentTemplate).where(DynamicContentTemplate.is_system.is_(True))
        ).all()
    }
    assert "product_grid_2x2" in slugs
    assert "product_hero_promo" in slugs
    assert "promotion_board_3x2" in slugs

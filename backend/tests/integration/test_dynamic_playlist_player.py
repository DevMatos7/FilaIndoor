"""DRC-3 — Dynamic Playlist & Player."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.modules.dynamic_content.content_service import DynamicContentService
from app.modules.dynamic_content.models import DynamicContentTemplate
from app.modules.dynamic_content.templates import ensure_system_templates
from app.modules.org.models.entities import Store
from app.modules.queue.models.entities import Display
from app.modules.retail.models import RetailPrice, RetailProduct, RetailSyncWatermark
from app.modules.retail.providers.mock import MockRetailDataProvider
from app.modules.retail.sync_service import RetailSyncService
from app.modules.signage.models import PlaylistItem
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


def _make_table(db, store_id: str, *, name: str = "Tabela QA", items_per_page: int = 8, page_dur: int = 8, mode: str = "FULL_CYCLE", total: int | None = None, product_limit: int = 6):
    ensure_system_templates(db)
    tpl = db.scalar(select(DynamicContentTemplate).where(DynamicContentTemplate.slug == "price_table_clean"))
    products = list(db.scalars(select(RetailProduct)).all())[:product_limit]
    cfg = {
        "items_per_page": items_per_page,
        "page_duration_seconds": page_dur,
        "duration_mode": mode,
        "title": name,
    }
    if total is not None:
        cfg["total_duration_seconds"] = total
    svc = DynamicContentService(db)
    return svc.create_content(
        store_id,
        {
            "name": name,
            "selection_mode": "MANUAL",
            "template_id": tpl.id,
            "config": cfg,
            "products": [{"product_id": p.id, "position": i} for i, p in enumerate(products)],
        },
    )


def test_media_backfill_default_and_dynamic_add(client, auth_header, seeded, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    from app.core.config import get_settings

    get_settings.cache_clear()
    media_root()

    db = seeded["db"]
    store_id = seeded["store"].id
    _seed_retail(db, store_id)
    asset = _upload(client, auth_header, store_id, "Img")
    pl = client.post(
        "/api/v1/playlists",
        json={"store_id": store_id, "name": "Mista", "is_default": True},
        headers=auth_header,
    ).json()

    media = client.post(
        f"/api/v1/playlists/{pl['id']}/items",
        json={"asset_id": asset["id"]},
        headers=auth_header,
    )
    assert media.status_code == 201, media.text
    assert media.json()["items"][0]["item_type"] == "MEDIA"
    assert media.json()["items"][0]["asset_id"] == asset["id"]

    table = _make_table(db, store_id)
    # ensure snapshot for duration
    DynamicContentService(db).preview(table["id"], store_id)

    dyn = client.post(
        f"/api/v1/playlists/{pl['id']}/items",
        json={"item_type": "DYNAMIC", "dynamic_content_id": table["id"]},
        headers=auth_header,
    )
    assert dyn.status_code == 201, dyn.text
    items = dyn.json()["items"]
    assert len(items) == 2
    assert items[1]["item_type"] == "DYNAMIC"
    assert items[1]["dynamic_content_id"] == table["id"]
    assert items[1]["asset_id"] is None
    assert items[1]["duration_source"] == "SOURCE"


def test_invalid_item_combinations(client, auth_header, seeded, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    from app.core.config import get_settings

    get_settings.cache_clear()
    media_root()
    db = seeded["db"]
    store_id = seeded["store"].id
    _seed_retail(db, store_id)
    asset = _upload(client, auth_header, store_id, "X")
    table = _make_table(db, store_id)
    pl = client.post(
        "/api/v1/playlists",
        json={"store_id": store_id, "name": "Inv"},
        headers=auth_header,
    ).json()

    both = client.post(
        f"/api/v1/playlists/{pl['id']}/items",
        json={"asset_id": asset["id"], "dynamic_content_id": table["id"], "item_type": "MEDIA"},
        headers=auth_header,
    )
    assert both.status_code == 422

    empty = client.post(
        f"/api/v1/playlists/{pl['id']}/items",
        json={"item_type": "DYNAMIC"},
        headers=auth_header,
    )
    assert empty.status_code == 422


def test_cross_store_dynamic_rejected(client, auth_header, seeded, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    from app.core.config import get_settings

    get_settings.cache_clear()
    media_root()
    db = seeded["db"]
    store_a = seeded["store"].id
    store_b = Store(company_id=seeded["company"].id, name="Loja B", timezone="America/Cuiaba")
    db.add(store_b)
    db.commit()
    db.refresh(store_b)
    _seed_retail(db, store_a)
    ensure_system_templates(db)
    from app.modules.dynamic_content.models import DynamicContent

    tpl = db.scalar(select(DynamicContentTemplate).where(DynamicContentTemplate.slug == "price_table_clean"))
    foreign = DynamicContent(
        store_id=store_b.id,
        name="Tabela B",
        content_type="PRICE_TABLE",
        selection_mode="MANUAL",
        template_id=tpl.id,
        config={},
        active=True,
    )
    db.add(foreign)
    db.commit()
    db.refresh(foreign)
    pl = client.post(
        "/api/v1/playlists",
        json={"store_id": store_a, "name": "A"},
        headers=auth_header,
    ).json()
    r = client.post(
        f"/api/v1/playlists/{pl['id']}/items",
        json={"item_type": "DYNAMIC", "dynamic_content_id": foreign.id},
        headers=auth_header,
    )
    assert r.status_code == 422


def test_usage_count_and_delete_blocked(client, auth_header, seeded, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    from app.core.config import get_settings

    get_settings.cache_clear()
    media_root()
    db = seeded["db"]
    store_id = seeded["store"].id
    _seed_retail(db, store_id)
    table = _make_table(db, store_id)
    DynamicContentService(db).preview(table["id"], store_id)
    pl = client.post(
        "/api/v1/playlists",
        json={"store_id": store_id, "name": "Uso"},
        headers=auth_header,
    ).json()
    client.post(
        f"/api/v1/playlists/{pl['id']}/items",
        json={"item_type": "DYNAMIC", "dynamic_content_id": table["id"]},
        headers=auth_header,
    )
    detail = client.get(f"/api/v1/dynamic-content/{table['id']}", params={"store_id": store_id}, headers=auth_header)
    assert detail.status_code == 200
    assert detail.json()["usage_count"] >= 1

    deleted = client.delete(
        f"/api/v1/dynamic-content/{table['id']}",
        params={"store_id": store_id},
        headers=auth_header,
    )
    assert deleted.status_code == 409


def test_player_config_mixed_and_dynamic_endpoint(client, auth_header, seeded, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    from app.core.config import get_settings

    get_settings.cache_clear()
    media_root()
    db = seeded["db"]
    store_id = seeded["store"].id
    _seed_retail(db, store_id)
    asset = _upload(client, auth_header, store_id, "Campanha")
    table = _make_table(db, store_id, items_per_page=4, page_dur=8, mode="FULL_CYCLE", product_limit=8)
    snap = DynamicContentService(db).preview(table["id"], store_id)
    assert snap["pagination"]["total_duration_seconds"] == snap["pagination"]["page_count"] * 8

    pl = client.post(
        "/api/v1/playlists",
        json={"store_id": store_id, "name": "TV", "is_default": True},
        headers=auth_header,
    ).json()
    client.post(
        f"/api/v1/playlists/{pl['id']}/items",
        json={"asset_id": asset["id"], "duration_seconds": 10},
        headers=auth_header,
    )
    client.post(
        f"/api/v1/playlists/{pl['id']}/items",
        json={"item_type": "DYNAMIC", "dynamic_content_id": table["id"]},
        headers=auth_header,
    )

    display = Display(
        store_id=store_id,
        department_id=seeded["department"].id,
        queue_id=seeded["queue"].id,
        name="TV DRC3",
        code="TV-DRC3",
        token="display-drc3-token",
        audio_enabled=False,
        playlist_id=pl["id"],
    )
    db.add(display)
    db.commit()

    cfg = client.get("/api/v1/player/config", headers={"X-Display-Token": "display-drc3-token"})
    assert cfg.status_code == 200, cfg.text
    playlist = cfg.json()["playlist"]
    assert len(playlist) == 2
    assert playlist[0]["item_type"] == "MEDIA"
    assert playlist[0]["type"] == "IMAGE"
    assert playlist[1]["item_type"] == "DYNAMIC"
    assert playlist[1]["dynamic_content"]["id"] == table["id"]
    assert playlist[1]["duration_seconds"] == snap["pagination"]["total_duration_seconds"]

    # player dynamic
    r1 = client.get(
        f"/api/v1/player/dynamic-content/{table['id']}",
        headers={"X-Display-Token": "display-drc3-token"},
    )
    assert r1.status_code == 200, r1.text
    body = r1.json()
    assert body["type"] == "PRICE_TABLE"
    assert body["content_hash"]
    assert "pages" in body
    etag = r1.headers.get("etag")
    assert etag

    r304 = client.get(
        f"/api/v1/player/dynamic-content/{table['id']}",
        headers={"X-Display-Token": "display-drc3-token", "If-None-Match": etag},
    )
    assert r304.status_code == 304

    # price change → hash change
    prod = db.get(RetailProduct, body["pages"][0]["items"][0]["product_id"])
    price = db.scalar(
        select(RetailPrice).where(
            RetailPrice.store_id == store_id,
            RetailPrice.product_id == prod.id,
            RetailPrice.price_kind == "REGULAR",
            RetailPrice.active.is_(True),
        )
    )
    old_hash = body["content_hash"]
    price.amount = 8.99
    # bump watermark so ensure_current regenerates
    wm = db.scalar(
        select(RetailSyncWatermark).where(
            RetailSyncWatermark.store_id == store_id, RetailSyncWatermark.entity == "PRICE"
        )
    )
    wm.watermark_value = "changed-price"
    db.commit()

    r2 = client.get(
        f"/api/v1/player/dynamic-content/{table['id']}",
        headers={"X-Display-Token": "display-drc3-token"},
    )
    assert r2.status_code == 200
    assert r2.json()["content_hash"] != old_hash


def test_player_store_isolation_and_inactive(client, auth_header, seeded, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    from app.core.config import get_settings

    get_settings.cache_clear()
    media_root()
    db = seeded["db"]
    store_a = seeded["store"].id
    store_b = Store(company_id=seeded["company"].id, name="Outra", timezone="America/Cuiaba")
    db.add(store_b)
    db.commit()
    db.refresh(store_b)
    _seed_retail(db, store_a)
    ensure_system_templates(db)
    from app.modules.dynamic_content.models import DynamicContent

    tpl = db.scalar(select(DynamicContentTemplate).where(DynamicContentTemplate.slug == "price_table_clean"))
    foreign = DynamicContent(
        store_id=store_b.id,
        name="Tabela B",
        content_type="PRICE_TABLE",
        selection_mode="MANUAL",
        template_id=tpl.id,
        config={},
        active=True,
    )
    db.add(foreign)
    db.commit()
    db.refresh(foreign)

    display = Display(
        store_id=store_a,
        department_id=seeded["department"].id,
        queue_id=seeded["queue"].id,
        name="TV A",
        code="TV-A",
        token="display-iso-token",
        audio_enabled=False,
    )
    db.add(display)
    db.commit()

    denied = client.get(
        f"/api/v1/player/dynamic-content/{foreign.id}",
        headers={"X-Display-Token": "display-iso-token"},
    )
    assert denied.status_code == 403

    table_a = _make_table(db, store_a, name="Inativa")
    DynamicContentService(db).preview(table_a["id"], store_a)
    # soft-delete without usage
    svc = DynamicContentService(db)
    row = svc._get_owned(table_a["id"], store_a)
    row.active = False
    db.commit()

    inactive = client.get(
        f"/api/v1/player/dynamic-content/{table_a['id']}",
        headers={"X-Display-Token": "display-iso-token"},
    )
    assert inactive.status_code == 404


def test_fixed_and_full_cycle_duration(seeded):
    db = seeded["db"]
    store_id = seeded["store"].id
    _seed_retail(db, store_id)
    full = _make_table(db, store_id, name="Full", items_per_page=4, page_dur=8, mode="FULL_CYCLE", product_limit=8)
    snap = DynamicContentService(db).preview(full["id"], store_id)
    assert snap["pagination"]["duration_mode"] == "FULL_CYCLE"
    assert snap["pagination"]["total_duration_seconds"] == snap["pagination"]["page_count"] * 8

    fixed = _make_table(db, store_id, name="Fixed", items_per_page=4, page_dur=8, mode="FIXED", total=40, product_limit=8)
    snap_f = DynamicContentService(db).preview(fixed["id"], store_id)
    assert snap_f["pagination"]["duration_mode"] == "FIXED"
    assert snap_f["pagination"]["total_duration_seconds"] == 40


def test_existing_playlist_items_default_media(seeded):
    """create_all + default item_type MEDIA for legacy-style inserts."""
    db = seeded["db"]
    from app.modules.signage.models import MediaAsset, Playlist

    pl = Playlist(store_id=seeded["store"].id, name="Legacy", active=True)
    db.add(pl)
    db.flush()
    asset = MediaAsset(
        store_id=seeded["store"].id,
        name="Leg",
        media_type="IMAGE",
        mime_type="image/png",
        public_url="/media/x.png",
        duration_seconds=10,
        active=True,
    )
    db.add(asset)
    db.flush()
    item = PlaylistItem(playlist_id=pl.id, asset_id=asset.id, position=0, duration_seconds=10)
    db.add(item)
    db.commit()
    db.refresh(item)
    assert item.item_type == "MEDIA"
    assert item.dynamic_content_id is None

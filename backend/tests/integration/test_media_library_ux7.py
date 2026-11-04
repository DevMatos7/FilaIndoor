"""UX-7 — Media Library additive API tests."""

from app.modules.signage.models import Playlist, PlaylistItem
from app.modules.signage.service import SignageService

PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


def test_limits_update_usage_and_delete_block(client, auth_header, seeded, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    from app.core.config import get_settings

    get_settings.cache_clear()

    store_id = seeded["store"].id
    limits = client.get("/api/v1/media/limits", headers=auth_header)
    assert limits.status_code == 200
    assert "image_max_mb" in limits.json()

    up = client.post(
        "/api/v1/media",
        data={"store_id": store_id, "name": "UX7 Promo", "duration_seconds": "8"},
        files={"file": ("promo.png", PNG_1X1, "image/png")},
        headers=auth_header,
    )
    assert up.status_code == 201, up.text
    asset_id = up.json()["id"]
    assert up.json().get("usage_count") == 0

    patched = client.patch(
        f"/api/v1/media/{asset_id}",
        json={"store_id": store_id, "name": "UX7 Promo Renomeado", "duration_seconds": 12},
        headers=auth_header,
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["name"] == "UX7 Promo Renomeado"
    assert patched.json()["duration_seconds"] == 12

    # attach to playlist → delete blocked
    db = seeded["db"]
    pl = Playlist(store_id=store_id, name="PL UX7")
    db.add(pl)
    db.flush()
    db.add(PlaylistItem(playlist_id=pl.id, asset_id=asset_id, position=0, duration_seconds=10))
    db.commit()

    listed = client.get("/api/v1/media", params={"store_id": store_id}, headers=auth_header)
    row = next(i for i in listed.json() if i["id"] == asset_id)
    assert row["usage_count"] >= 1

    blocked = client.delete(
        f"/api/v1/media/{asset_id}",
        params={"store_id": store_id},
        headers=auth_header,
    )
    assert blocked.status_code == 409, blocked.text

    # remove playlist item → soft delete ok
    from sqlalchemy import delete

    db.execute(delete(PlaylistItem).where(PlaylistItem.asset_id == asset_id))
    db.commit()
    ok = client.delete(
        f"/api/v1/media/{asset_id}",
        params={"store_id": store_id},
        headers=auth_header,
    )
    assert ok.status_code == 200
    assert ok.json()["active"] is False


def test_store_isolation_on_get(client, auth_header, seeded, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    from app.core.config import get_settings
    from app.modules.org.models.entities import Company, Store

    get_settings.cache_clear()

    store_id = seeded["store"].id
    db = seeded["db"]
    up = client.post(
        "/api/v1/media",
        data={"store_id": store_id, "name": "Isolado", "duration_seconds": "5"},
        files={"file": ("a.png", PNG_1X1, "image/png")},
        headers=auth_header,
    )
    assert up.status_code == 201
    asset_id = up.json()["id"]

    other = Company(name="Outra", external_code="OUT")
    db.add(other)
    db.flush()
    other_store = Store(company_id=other.id, name="Loja Outra")
    db.add(other_store)
    db.commit()

    forbidden = client.get(
        f"/api/v1/media/{asset_id}",
        params={"store_id": other_store.id},
        headers=auth_header,
    )
    assert forbidden.status_code == 403

    ok = client.get(
        f"/api/v1/media/{asset_id}",
        params={"store_id": store_id},
        headers=auth_header,
    )
    assert ok.status_code == 200


def test_web_and_filter_still_work(client, auth_header, seeded):
    store_id = seeded["store"].id
    web = client.post(
        "/api/v1/media/web",
        json={"store_id": store_id, "name": "Site UX7", "url": "https://example.com/x"},
        headers=auth_header,
    )
    assert web.status_code == 201
    listed = client.get(
        "/api/v1/media",
        params={"store_id": store_id, "media_type": "WEB"},
        headers=auth_header,
    )
    assert listed.status_code == 200
    assert any(i["name"] == "Site UX7" for i in listed.json())


def test_usage_count_batch_no_crash(db_session, seeded):
    svc = SignageService(db_session)
    assert svc._usage_counts([]) == {}
    listed = svc.list_assets(store_id=seeded["store"].id)
    assert isinstance(listed, list)

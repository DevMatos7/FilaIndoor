"""UX-8 — Playlist Studio additive API tests."""

from app.modules.queue.models.entities import Display
from app.modules.signage.models import Channel, Schedule
from app.modules.signage.storage import media_root

PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


def _upload(client, auth_header, store_id: str, name: str):
    r = client.post(
        "/api/v1/media",
        data={"store_id": store_id, "name": name, "duration_seconds": "5"},
        files={"file": (f"{name}.png", PNG_1X1, "image/png")},
        headers=auth_header,
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_reorder_abc_to_cab_and_player_duration(client, auth_header, seeded, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    from app.core.config import get_settings

    get_settings.cache_clear()
    media_root()
    store_id = seeded["store"].id

    a = _upload(client, auth_header, store_id, "A")
    b = _upload(client, auth_header, store_id, "B")
    c = _upload(client, auth_header, store_id, "C")

    pl = client.post(
        "/api/v1/playlists",
        json={"store_id": store_id, "name": "Studio ABC", "is_default": True},
        headers=auth_header,
    ).json()
    pl_id = pl["id"]
    assert pl["total_duration_seconds"] == 0
    assert pl["usage_count"] == 0

    for asset in (a, b, c):
        r = client.post(
            f"/api/v1/playlists/{pl_id}/items",
            json={"asset_id": asset["id"], "duration_seconds": 10},
            headers=auth_header,
        )
        assert r.status_code == 201, r.text

    detail = client.get(f"/api/v1/playlists/{pl_id}", headers=auth_header).json()
    ids = [i["id"] for i in detail["items"]]
    assert len(ids) == 3
    assert detail["total_duration_seconds"] == 30

    # A,B,C → C,A,B
    reordered = [ids[2], ids[0], ids[1]]
    out = client.patch(
        f"/api/v1/playlists/{pl_id}/items/reorder",
        json={"item_ids": reordered, "store_id": store_id},
        headers=auth_header,
    )
    assert out.status_code == 200, out.text
    names = [i["asset"]["name"] for i in out.json()["items"]]
    assert names == ["C", "A", "B"]

    # duration on C
    client.patch(
        f"/api/v1/playlists/{pl_id}/items/{reordered[0]}",
        json={"duration_seconds": 22, "store_id": store_id},
        headers=auth_header,
    )

    db = seeded["db"]
    display = Display(
        store_id=store_id,
        department_id=seeded["department"].id,
        queue_id=seeded["queue"].id,
        name="TV Studio",
        code="TV-ST",
        token="display-studio-token",
        playlist_id=pl_id,
        active=True,
    )
    db.add(display)
    db.commit()

    cfg = client.get("/api/v1/player/config", headers={"X-Display-Token": "display-studio-token"})
    assert cfg.status_code == 200
    playlist = cfg.json()["playlist"]
    assert [p["name"] for p in playlist] == ["C", "A", "B"]
    assert playlist[0]["duration_seconds"] == 22


def test_bulk_add_and_delete_blocked_when_in_use(client, auth_header, seeded, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    from app.core.config import get_settings

    get_settings.cache_clear()
    store_id = seeded["store"].id
    a1 = _upload(client, auth_header, store_id, "Bulk1")
    a2 = _upload(client, auth_header, store_id, "Bulk2")

    pl = client.post(
        "/api/v1/playlists",
        json={"store_id": store_id, "name": "Bulk PL"},
        headers=auth_header,
    ).json()
    pl_id = pl["id"]

    bulk = client.post(
        f"/api/v1/playlists/{pl_id}/items/bulk",
        json={"asset_ids": [a1["id"], a2["id"]], "store_id": store_id},
        headers=auth_header,
    )
    assert bulk.status_code == 201, bulk.text
    assert len(bulk.json()["items"]) == 2

    # attach channel default → delete blocked
    db = seeded["db"]
    ch = Channel(store_id=store_id, name="Canal Bulk", default_playlist_id=pl_id)
    db.add(ch)
    db.commit()

    listed = client.get("/api/v1/playlists", params={"store_id": store_id}, headers=auth_header)
    row = next(p for p in listed.json() if p["id"] == pl_id)
    assert row["usage_count"] >= 1

    blocked = client.delete(
        f"/api/v1/playlists/{pl_id}",
        params={"store_id": store_id},
        headers=auth_header,
    )
    assert blocked.status_code == 409, blocked.text

    ch.default_playlist_id = None
    db.commit()
    ok = client.delete(f"/api/v1/playlists/{pl_id}", params={"store_id": store_id}, headers=auth_header)
    assert ok.status_code == 200
    assert ok.json()["active"] is False


def test_cross_store_asset_rejected(client, auth_header, seeded, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    from app.core.config import get_settings
    from app.modules.org.models.entities import Company, Store

    get_settings.cache_clear()
    store_id = seeded["store"].id
    db = seeded["db"]

    other = Company(name="Outra Co", external_code="OX")
    db.add(other)
    db.flush()
    other_store = Store(company_id=other.id, name="Loja X")
    db.add(other_store)
    db.commit()

    foreign = _upload(client, auth_header, other_store.id, "Foreign")
    pl = client.post(
        "/api/v1/playlists",
        json={"store_id": store_id, "name": "Iso"},
        headers=auth_header,
    ).json()

    bad = client.post(
        f"/api/v1/playlists/{pl['id']}/items",
        json={"asset_id": foreign["id"]},
        headers=auth_header,
    )
    assert bad.status_code == 422


def test_schedule_usage_blocks_delete(client, auth_header, seeded, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    from app.core.config import get_settings

    get_settings.cache_clear()
    store_id = seeded["store"].id
    pl = client.post(
        "/api/v1/playlists",
        json={"store_id": store_id, "name": "Sched PL"},
        headers=auth_header,
    ).json()
    db = seeded["db"]
    ch = Channel(store_id=store_id, name="Ch Sched")
    db.add(ch)
    db.flush()
    db.add(Schedule(channel_id=ch.id, playlist_id=pl["id"], name="Agenda", active=True))
    db.commit()

    blocked = client.delete(
        f"/api/v1/playlists/{pl['id']}",
        params={"store_id": store_id},
        headers=auth_header,
    )
    assert blocked.status_code == 409

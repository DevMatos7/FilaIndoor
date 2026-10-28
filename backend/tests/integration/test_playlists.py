from app.modules.queue.models.entities import Display
from app.modules.signage.storage import media_root

PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


def _upload(client, auth_header, store_id: str, name: str):
    files = {"file": (f"{name}.png", PNG_1X1, "image/png")}
    data = {"store_id": store_id, "name": name, "duration_seconds": "5"}
    r = client.post("/api/v1/media", data=data, files=files, headers=auth_header)
    assert r.status_code == 201, r.text
    return r.json()


def test_playlist_crud_reorder_and_player(client, auth_header, seeded, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    from app.core.config import get_settings

    get_settings.cache_clear()
    media_root()

    store_id = seeded["store"].id
    a1 = _upload(client, auth_header, store_id, "Slide A")
    a2 = _upload(client, auth_header, store_id, "Slide B")

    created = client.post(
        "/api/v1/playlists",
        json={"store_id": store_id, "name": "Playlist Teste", "is_default": True},
        headers=auth_header,
    )
    assert created.status_code == 201, created.text
    pl_id = created.json()["id"]

    for asset in (a1, a2):
        add = client.post(
            f"/api/v1/playlists/{pl_id}/items",
            json={"asset_id": asset["id"], "duration_seconds": 7},
            headers=auth_header,
        )
        assert add.status_code == 201, add.text

    detail = client.get(f"/api/v1/playlists/{pl_id}", headers=auth_header)
    assert detail.status_code == 200
    items = detail.json()["items"]
    assert len(items) == 2
    assert items[0]["asset_id"] == a1["id"]

    # reordena B antes de A
    reorder = client.patch(
        f"/api/v1/playlists/{pl_id}/items/reorder",
        json={"item_ids": [items[1]["id"], items[0]["id"]]},
        headers=auth_header,
    )
    assert reorder.status_code == 200, reorder.text
    assert reorder.json()["items"][0]["asset_id"] == a2["id"]

    # após reorder: [B, A] — ajusta duração do primeiro (B)
    reordered_items = reorder.json()["items"]
    patch_dur = client.patch(
        f"/api/v1/playlists/{pl_id}/items/{reordered_items[0]['id']}",
        json={"duration_seconds": 15},
        headers=auth_header,
    )
    assert patch_dur.status_code == 200

    db = seeded["db"]
    display = Display(
        store_id=store_id,
        department_id=seeded["department"].id,
        queue_id=seeded["queue"].id,
        name="TV PL",
        code="TV-PL",
        token="display-playlist-token",
        audio_enabled=False,
        playlist_id=pl_id,
    )
    db.add(display)
    db.commit()

    cfg = client.get("/api/v1/player/config", headers={"X-Display-Token": "display-playlist-token"})
    assert cfg.status_code == 200, cfg.text
    playlist = cfg.json()["playlist"]
    assert len(playlist) == 2
    assert playlist[0]["name"] == "Slide B"
    assert playlist[0]["duration_seconds"] == 15
    assert playlist[1]["name"] == "Slide A"

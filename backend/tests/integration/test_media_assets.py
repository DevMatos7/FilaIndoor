from app.modules.signage.storage import media_root


PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


def test_upload_list_preview_delete(client, auth_header, seeded, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    from app.core.config import get_settings

    get_settings.cache_clear()

    store_id = seeded["store"].id
    files = {"file": ("promo.png", PNG_1X1, "image/png")}
    data = {"store_id": store_id, "name": "Promo Teste", "duration_seconds": "8"}
    up = client.post("/api/v1/media", data=data, files=files, headers=auth_header)
    assert up.status_code == 201, up.text
    body = up.json()
    assert body["media_type"] == "IMAGE"
    assert body["public_url"].startswith("/media/files/")
    assert body["size_bytes"] == len(PNG_1X1)

    listed = client.get("/api/v1/media", params={"store_id": store_id}, headers=auth_header)
    assert listed.status_code == 200
    assert any(i["id"] == body["id"] for i in listed.json())

    detail = client.get(f"/api/v1/media/{body['id']}", headers=auth_header)
    assert detail.status_code == 200
    assert detail.json()["name"] == "Promo Teste"

    # arquivo físico existe
    key = body["public_url"].replace("/media/files/", "", 1)
    assert (media_root() / key).is_file()

    deleted = client.delete(f"/api/v1/media/{body['id']}", headers=auth_header)
    assert deleted.status_code == 200
    assert deleted.json()["active"] is False

    listed2 = client.get("/api/v1/media", params={"store_id": store_id}, headers=auth_header)
    assert all(i["id"] != body["id"] for i in listed2.json())


def test_reject_unsupported_type(client, auth_header, seeded, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    from app.core.config import get_settings

    get_settings.cache_clear()

    files = {"file": ("x.bin", b"not-a-media", "application/octet-stream")}
    data = {"store_id": seeded["store"].id, "name": "Inválido"}
    r = client.post("/api/v1/media", data=data, files=files, headers=auth_header)
    assert r.status_code == 422


def test_web_media_and_player_playlist(client, auth_header, seeded, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    from app.core.config import get_settings
    from app.modules.queue.models.entities import Display

    get_settings.cache_clear()

    store_id = seeded["store"].id
    web = client.post(
        "/api/v1/media/web",
        json={
            "store_id": store_id,
            "name": "Banner Site",
            "url": "https://example.com/promo",
            "duration_seconds": 20,
        },
        headers=auth_header,
    )
    assert web.status_code == 201, web.text

    db = seeded["db"]
    display = Display(
        store_id=store_id,
        department_id=seeded["department"].id,
        queue_id=seeded["queue"].id,
        name="TV Media",
        code="TV-M",
        token="display-media-token",
        audio_enabled=False,
    )
    db.add(display)
    db.commit()

    cfg = client.get("/api/v1/player/config", headers={"X-Display-Token": "display-media-token"})
    assert cfg.status_code == 200, cfg.text
    playlist = cfg.json()["playlist"]
    assert any(p["name"] == "Banner Site" and p["type"] == "WEB" for p in playlist)

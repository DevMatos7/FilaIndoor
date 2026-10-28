from datetime import datetime

from app.modules.queue.models.entities import Display


PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


def test_channel_schedule_priority_conflict_and_player(client, auth_header, seeded, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    from app.core.config import get_settings

    get_settings.cache_clear()

    store_id = seeded["store"].id
    # mídia + playlist
    up = client.post(
        "/api/v1/media",
        data={"store_id": store_id, "name": "Slide Canal", "duration_seconds": "5"},
        files={"file": ("c.png", PNG_1X1, "image/png")},
        headers=auth_header,
    )
    assert up.status_code == 201, up.text
    asset_id = up.json()["id"]

    pl = client.post(
        "/api/v1/playlists",
        json={"store_id": store_id, "name": "PL Canal", "is_default": True},
        headers=auth_header,
    )
    assert pl.status_code == 201
    pl_id = pl.json()["id"]
    client.post(f"/api/v1/playlists/{pl_id}/items", json={"asset_id": asset_id}, headers=auth_header)

    pl2 = client.post(
        "/api/v1/playlists",
        json={"store_id": store_id, "name": "PL Emergência"},
        headers=auth_header,
    )
    pl2_id = pl2.json()["id"]
    client.post(f"/api/v1/playlists/{pl2_id}/items", json={"asset_id": asset_id, "duration_seconds": 3}, headers=auth_header)

    ch = client.post(
        "/api/v1/channels",
        json={"store_id": store_id, "name": "Canal Teste", "default_playlist_id": pl_id},
        headers=auth_header,
    )
    assert ch.status_code == 201, ch.text
    channel_id = ch.json()["id"]

    client.post(
        "/api/v1/screen-groups",
        json={"store_id": store_id, "channel_id": channel_id, "name": "Grupo 1"},
        headers=auth_header,
    )

    # duas agendas NORMAL sobrepostas → conflito
    s1 = client.post(
        "/api/v1/schedules",
        json={
            "channel_id": channel_id,
            "playlist_id": pl_id,
            "name": "Agenda A",
            "start_time": "00:00",
            "end_time": "23:59",
            "days_of_week": [0, 1, 2, 3, 4, 5, 6],
            "priority": "NORMAL",
        },
        headers=auth_header,
    )
    assert s1.status_code == 201, s1.text
    s2 = client.post(
        "/api/v1/schedules",
        json={
            "channel_id": channel_id,
            "playlist_id": pl_id,
            "name": "Agenda B",
            "start_time": "00:00",
            "end_time": "23:59",
            "days_of_week": [0, 1, 2, 3, 4, 5, 6],
            "priority": "NORMAL",
        },
        headers=auth_header,
    )
    assert s2.status_code == 201

    conflicts = client.get(f"/api/v1/channels/{channel_id}/conflicts", headers=auth_header)
    assert conflicts.status_code == 200
    assert len(conflicts.json()["conflicts"]) >= 1

    # EMERGENCY vence
    client.post(
        "/api/v1/schedules",
        json={
            "channel_id": channel_id,
            "playlist_id": pl2_id,
            "name": "Urgente",
            "start_time": "00:00",
            "end_time": "23:59",
            "days_of_week": [0, 1, 2, 3, 4, 5, 6],
            "priority": "EMERGENCY",
        },
        headers=auth_header,
    )
    now = client.get(f"/api/v1/channels/{channel_id}/now", headers=auth_header)
    assert now.status_code == 200
    assert now.json()["schedule"]["priority"] == "EMERGENCY"
    assert now.json()["playlist_id"] == pl2_id

    db = seeded["db"]
    display = Display(
        store_id=store_id,
        department_id=seeded["department"].id,
        queue_id=seeded["queue"].id,
        name="TV Canal",
        code="TV-CH",
        token="display-channel-token",
        audio_enabled=False,
        channel_id=channel_id,
    )
    db.add(display)
    db.commit()

    cfg = client.get("/api/v1/player/config", headers={"X-Display-Token": "display-channel-token"})
    assert cfg.status_code == 200, cfg.text
    body = cfg.json()
    assert body["channel"]["source"] == "schedule"
    assert body["channel"]["schedule"]["priority"] == "EMERGENCY"
    assert len(body["playlist"]) >= 1

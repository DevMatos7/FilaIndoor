from app.modules.queue.models.entities import Display


def test_pairing_enroll_heartbeat_status(client, auth_header, seeded):
    store_id = seeded["store"].id
    dept_id = seeded["department"].id
    queue_id = seeded["queue"].id

    display = Display(
        store_id=store_id,
        department_id=dept_id,
        queue_id=queue_id,
        name="TV Teste",
        code="TV-T1",
        token="display-test-token",
        audio_enabled=True,
    )
    seeded["db"].add(display)
    seeded["db"].commit()
    seeded["db"].refresh(display)

    pair = client.post(
        "/api/v1/devices/pairing",
        json={"device_uuid": "uuid-tv-test-1", "device_type": "DISPLAY", "app_version": "1.0.0", "name": "TV Nova"},
    )
    assert pair.status_code == 200, pair.text
    body = pair.json()
    assert body["pairing_code"]
    assert body["already_enrolled"] is False
    device_id = body["id"]
    code = body["pairing_code"]

    enroll = client.post(
        "/api/v1/devices/enroll",
        json={
            "pairing_code": code,
            "store_id": store_id,
            "department_id": dept_id,
            "display_id": display.id,
            "name": "TV Açougue Homolog",
        },
        headers=auth_header,
    )
    assert enroll.status_code == 200, enroll.text
    enrolled = enroll.json()
    assert enrolled["store_id"] == store_id
    assert enrolled["display_id"] == display.id
    assert enrolled["enrolled"] is True

    hb = client.post(
        f"/api/v1/devices/{device_id}/heartbeat",
        json={"online": True, "app_version": "1.0.1", "free_storage_mb": 2048, "playlist_version": 3},
        headers={"X-Device-UUID": "uuid-tv-test-1"},
    )
    assert hb.status_code == 200, hb.text
    assert hb.json()["status"] == "ONLINE"
    assert hb.json()["app_version"] == "1.0.1"

    listed = client.get("/api/v1/devices", headers=auth_header)
    assert listed.status_code == 200
    row = next(d for d in listed.json() if d["id"] == device_id)
    assert row["status"] == "ONLINE"

    heartbeats = client.get(f"/api/v1/devices/{device_id}/heartbeats", headers=auth_header)
    assert heartbeats.status_code == 200
    assert len(heartbeats.json()) >= 1

    disabled = client.post(f"/api/v1/devices/{device_id}/disable", headers=auth_header)
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "DISABLED"

    denied = client.post(
        f"/api/v1/devices/{device_id}/heartbeat",
        json={"online": True},
        headers={"X-Device-UUID": "uuid-tv-test-1"},
    )
    assert denied.status_code == 422

    enabled = client.post(f"/api/v1/devices/{device_id}/enable", headers=auth_header)
    assert enabled.status_code == 200
    assert enabled.json()["status"] in {"OFFLINE", "ONLINE", "DEGRADED"}


def test_player_config_ensures_device(client, seeded):
    store_id = seeded["store"].id
    dept_id = seeded["department"].id
    queue_id = seeded["queue"].id
    display = Display(
        store_id=store_id,
        department_id=dept_id,
        queue_id=queue_id,
        name="TV Player",
        code="TV-P1",
        token="display-player-token",
        audio_enabled=False,
    )
    seeded["db"].add(display)
    seeded["db"].commit()

    cfg = client.get("/api/v1/player/config", headers={"X-Display-Token": "display-player-token"})
    assert cfg.status_code == 200, cfg.text
    data = cfg.json()
    assert data["device"]["display_id"] == display.id
    assert data["device"]["enrolled"] is True
    assert "config_version" in data

    hb = client.post(
        f"/api/v1/devices/{data['device']['id']}/heartbeat",
        json={"online": True, "free_storage_mb": 1000},
        headers={"X-Display-Token": "display-player-token"},
    )
    assert hb.status_code == 200, hb.text
    assert hb.json()["status"] == "ONLINE"


def test_expired_or_invalid_pairing(client, auth_header, seeded):
    bad = client.post(
        "/api/v1/devices/enroll",
        json={"pairing_code": "000000", "store_id": seeded["store"].id},
        headers=auth_header,
    )
    assert bad.status_code == 404

"""UX-10 — Screen & Device Fleet."""

from datetime import timedelta

from sqlalchemy import select

from app.modules.devices.models import Device
from app.modules.devices.service import DEGRADED_SECONDS, ONLINE_SECONDS, DeviceService
from app.modules.org.models.entities import Company, Store
from app.modules.queue.models.entities import Display, utcnow
from app.modules.signage.models import Channel


PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


def test_fleet_store_scoped_and_no_raw_token(client, auth_header, seeded):
    store_id = seeded["store"].id
    display = Display(
        store_id=store_id,
        department_id=seeded["department"].id,
        queue_id=seeded["queue"].id,
        name="TV Açougue 01",
        code="TV-F1",
        token="secret-fleet-token-xyz",
        audio_enabled=True,
        active=True,
    )
    seeded["db"].add(display)
    seeded["db"].commit()

    fleet = client.get("/api/v1/devices/fleet", params={"store_id": store_id}, headers=auth_header)
    assert fleet.status_code == 200, fleet.text
    body = fleet.json()
    assert body["store_id"] == store_id
    assert body["heartbeat"]["online_seconds"] == ONLINE_SECONDS
    assert body["heartbeat"]["degraded_seconds"] == DEGRADED_SECONDS
    assert "summary" in body
    assert any(i["display_id"] == display.id for i in body["items"])
    assert "secret-fleet-token-xyz" not in fleet.text
    item = next(i for i in body["items"] if i["display_id"] == display.id)
    assert item["token_configured"] is True
    assert item["device_type"] == "DISPLAY"


def test_status_online_degraded_offline_disabled(client, auth_header, seeded):
    store_id = seeded["store"].id
    db = seeded["db"]
    now = utcnow()

    def make(name, code, token, last_seen, status="OFFLINE"):
        d = Display(
            store_id=store_id,
            name=name,
            code=code,
            token=token,
            active=True,
        )
        db.add(d)
        db.flush()
        DeviceService(db).ensure_for_display(d)
        device = db.scalar(select(Device).where(Device.display_id == d.id))
        device.last_seen_at = last_seen
        device.status = status
        return d

    make("Online TV", "TV-ON", "tok-on", now - timedelta(seconds=10))
    make("Degraded TV", "TV-DG", "tok-dg", now - timedelta(seconds=ONLINE_SECONDS + 30))
    make("Offline TV", "TV-OF", "tok-of", now - timedelta(seconds=DEGRADED_SECONDS + 60))
    make("Disabled TV", "TV-DI", "tok-di", now - timedelta(seconds=5), status="DISABLED")
    db.commit()

    fleet = client.get("/api/v1/devices/fleet", params={"store_id": store_id}, headers=auth_header).json()
    by_name = {i["name"]: i["status"] for i in fleet["items"] if i["device_type"] == "DISPLAY"}
    assert by_name["Online TV"] == "ONLINE"
    assert by_name["Degraded TV"] == "DEGRADED"
    assert by_name["Offline TV"] == "OFFLINE"
    assert by_name["Disabled TV"] == "DISABLED"

    ops = client.get("/api/v1/operations/overview", params={"store_id": store_id}, headers=auth_header)
    assert ops.status_code == 200
    cats = ops.json()["devices"]["categories"]["DISPLAY"]
    # Same thresholds: offline/degraded appear in CC attention items
    attention = {i["name"]: i["status"] for i in cats["items"]}
    assert attention.get("Offline TV") == "OFFLINE"
    assert attention.get("Degraded TV") == "DEGRADED"


def test_channel_assign_and_player_config(client, auth_header, seeded, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    from app.core.config import get_settings

    get_settings.cache_clear()
    store_id = seeded["store"].id
    db = seeded["db"]

    up = client.post(
        "/api/v1/media",
        data={"store_id": store_id, "name": "Slide F", "duration_seconds": "5"},
        files={"file": ("f.png", PNG, "image/png")},
        headers=auth_header,
    )
    assert up.status_code == 201, up.text
    pl_a = client.post(
        "/api/v1/playlists", json={"store_id": store_id, "name": "PLA"}, headers=auth_header
    ).json()
    pl_b = client.post(
        "/api/v1/playlists", json={"store_id": store_id, "name": "PLB"}, headers=auth_header
    ).json()
    client.post(
        f"/api/v1/playlists/{pl_a['id']}/items",
        json={"asset_id": up.json()["id"]},
        headers=auth_header,
    )
    client.post(
        f"/api/v1/playlists/{pl_b['id']}/items",
        json={"asset_id": up.json()["id"]},
        headers=auth_header,
    )

    ch_a = client.post(
        "/api/v1/channels",
        json={"store_id": store_id, "name": "Canal A", "default_playlist_id": pl_a["id"]},
        headers=auth_header,
    ).json()
    ch_b = client.post(
        "/api/v1/channels",
        json={"store_id": store_id, "name": "Canal B", "default_playlist_id": pl_b["id"]},
        headers=auth_header,
    ).json()

    display = Display(
        store_id=store_id,
        department_id=seeded["department"].id,
        queue_id=seeded["queue"].id,
        name="TV Channel",
        code="TV-CH-F",
        token="display-fleet-ch-token",
        channel_id=ch_a["id"],
        active=True,
    )
    db.add(display)
    db.commit()

    cfg = client.get("/api/v1/player/config", headers={"X-Display-Token": "display-fleet-ch-token"})
    assert cfg.status_code == 200
    ch_cfg = cfg.json().get("channel") or {}
    assert ch_cfg.get("id") == ch_a["id"] or ch_cfg.get("name") == "Canal A"

    assign = client.post(
        f"/api/v1/displays/{display.id}/channel",
        json={"channel_id": ch_b["id"], "store_id": store_id},
        headers=auth_header,
    )
    assert assign.status_code == 200, assign.text
    assert assign.json()["channel_id"] == ch_b["id"]
    assert assign.json().get("token") is None
    assert assign.json()["token_configured"] is True

    cfg2 = client.get("/api/v1/player/config", headers={"X-Display-Token": "display-fleet-ch-token"})
    assert cfg2.status_code == 200
    body = cfg2.json()
    ch = body.get("channel") or {}
    assert ch.get("id") == ch_b["id"] or ch.get("name") == "Canal B"
    assert len(body.get("playlist") or []) >= 1


def test_cross_store_channel_rejected(client, auth_header, seeded):
    store_id = seeded["store"].id
    db = seeded["db"]
    other = Company(name="Outra Fleet", external_code="UX10O")
    db.add(other)
    db.flush()
    other_store = Store(company_id=other.id, name="Loja Outra")
    db.add(other_store)
    db.flush()
    foreign_ch = Channel(store_id=other_store.id, name="Canal Outro")
    db.add(foreign_ch)
    display = Display(
        store_id=store_id,
        name="TV Iso",
        code="TV-ISO",
        token="tok-iso-fleet",
        active=True,
    )
    db.add(display)
    db.commit()

    bad = client.post(
        f"/api/v1/displays/{display.id}/channel",
        json={"channel_id": foreign_ch.id, "store_id": store_id},
        headers=auth_header,
    )
    assert bad.status_code == 422

    bad_patch = client.patch(
        f"/api/v1/displays/{display.id}",
        json={"channel_id": foreign_ch.id, "store_id": store_id},
        headers=auth_header,
    )
    assert bad_patch.status_code == 422


def test_fleet_edge_summary_and_programmed_label(client, auth_header, seeded, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    from app.core.config import get_settings

    get_settings.cache_clear()
    store_id = seeded["store"].id
    up = client.post(
        "/api/v1/media",
        data={"store_id": store_id, "name": "M", "duration_seconds": "5"},
        files={"file": ("m.png", PNG, "image/png")},
        headers=auth_header,
    )
    pl = client.post(
        "/api/v1/playlists", json={"store_id": store_id, "name": "PL Prog"}, headers=auth_header
    ).json()
    client.post(
        f"/api/v1/playlists/{pl['id']}/items",
        json={"asset_id": up.json()["id"]},
        headers=auth_header,
    )
    ch = client.post(
        "/api/v1/channels",
        json={"store_id": store_id, "name": "Canal Prog", "default_playlist_id": pl["id"]},
        headers=auth_header,
    ).json()
    display = Display(
        store_id=store_id,
        name="TV Prog",
        code="TV-PRG",
        token="tok-prog",
        channel_id=ch["id"],
        active=True,
    )
    seeded["db"].add(display)
    seeded["db"].commit()

    fleet = client.get("/api/v1/devices/fleet", params={"store_id": store_id}, headers=auth_header).json()
    assert "edge" in fleet
    assert fleet["edge"]["status"] in {"ONLINE", "DEGRADED"}
    item = next(i for i in fleet["items"] if i.get("display_id") == display.id)
    assert item["programmed"] is not None
    assert item["programmed"]["confirmed"] is False
    assert item["programmed"]["label"] == "Programado agora"
    assert item["channel"]["name"] == "Canal Prog"

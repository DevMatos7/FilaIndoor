"""UX-9 — Programming Studio: overview, conflicts, isolation, boundaries."""

from datetime import datetime, time

from app.modules.queue.models.entities import Display
from app.modules.signage.layout_service import LayoutService
from app.modules.signage.models import Channel, LayoutTemplate, Playlist, Schedule
from app.modules.signage.schedule_service import ScheduleService, schedule_matches
from app.modules.org.models.entities import Company, Store


PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


def _pl(client, auth, store_id, name):
    up = client.post(
        "/api/v1/media",
        data={"store_id": store_id, "name": f"M-{name}", "duration_seconds": "5"},
        files={"file": ("x.png", PNG, "image/png")},
        headers=auth,
    )
    assert up.status_code == 201, up.text
    pl = client.post(
        "/api/v1/playlists",
        json={"store_id": store_id, "name": name},
        headers=auth,
    )
    assert pl.status_code == 201
    client.post(
        f"/api/v1/playlists/{pl.json()['id']}/items",
        json={"asset_id": up.json()["id"]},
        headers=auth,
    )
    return pl.json()["id"]


def test_overview_current_matches_active_at_and_player(client, auth_header, seeded, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    from app.core.config import get_settings

    get_settings.cache_clear()
    store_id = seeded["store"].id
    pl_id = _pl(client, auth_header, store_id, "PL Now")
    pl2 = _pl(client, auth_header, store_id, "PL High")

    ch = client.post(
        "/api/v1/channels",
        json={"store_id": store_id, "name": "Canal UX9", "default_playlist_id": pl_id},
        headers=auth_header,
    )
    assert ch.status_code == 201, ch.text
    channel_id = ch.json()["id"]

    client.post(
        "/api/v1/schedules",
        json={
            "channel_id": channel_id,
            "playlist_id": pl_id,
            "name": "Normal Dia",
            "start_time": "00:00",
            "end_time": "23:59",
            "days_of_week": [0, 1, 2, 3, 4, 5, 6],
            "priority": "NORMAL",
        },
        headers=auth_header,
    )
    client.post(
        "/api/v1/schedules",
        json={
            "channel_id": channel_id,
            "playlist_id": pl2,
            "name": "High Dia",
            "start_time": "00:00",
            "end_time": "23:59",
            "days_of_week": [0, 1, 2, 3, 4, 5, 6],
            "priority": "HIGH",
        },
        headers=auth_header,
    )

    now = client.get(f"/api/v1/channels/{channel_id}/now", headers=auth_header)
    assert now.status_code == 200
    assert now.json()["source"] == "schedule"
    assert now.json()["schedule"]["name"] == "High Dia"
    assert now.json()["playlist_id"] == pl2

    overview = client.get(
        f"/api/v1/channels/{channel_id}/programming-overview",
        params={"store_id": store_id},
        headers=auth_header,
    )
    assert overview.status_code == 200
    body = overview.json()
    assert body["current"]["playlist_id"] == now.json()["playlist_id"]
    assert body["current"]["schedule"]["id"] == now.json()["schedule"]["id"]
    assert any(c["kind"] == "RESOLVED_BY_PRIORITY" for c in body["conflicts"])

    db = seeded["db"]
    display = Display(
        store_id=store_id,
        department_id=seeded["department"].id,
        queue_id=seeded["queue"].id,
        name="TV UX9",
        code="TV-UX9",
        token="display-ux9-token",
        channel_id=channel_id,
        active=True,
    )
    db.add(display)
    db.commit()
    cfg = client.get("/api/v1/player/config", headers={"X-Display-Token": "display-ux9-token"})
    assert cfg.status_code == 200
    assert cfg.json()["channel"]["source"] == "schedule"
    assert cfg.json()["channel"]["schedule"]["priority"] == "HIGH"
    assert len(cfg.json()["playlist"]) >= 1


def test_same_priority_ambiguous_and_emergency_vs_high(client, auth_header, seeded, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    from app.core.config import get_settings

    get_settings.cache_clear()
    store_id = seeded["store"].id
    pl = _pl(client, auth_header, store_id, "PL Amb")
    ch = client.post(
        "/api/v1/channels",
        json={"store_id": store_id, "name": "Canal Amb"},
        headers=auth_header,
    ).json()["id"]

    for name in ("A", "B"):
        r = client.post(
            "/api/v1/schedules",
            json={
                "channel_id": ch,
                "playlist_id": pl,
                "name": name,
                "start_time": "08:00",
                "end_time": "18:00",
                "days_of_week": [0, 1, 2, 3, 4, 5, 6],
                "priority": "NORMAL",
            },
            headers=auth_header,
        )
        assert r.status_code == 201, r.text

    structural = client.get(
        f"/api/v1/channels/{ch}/conflicts",
        params={"structural": True},
        headers=auth_header,
    )
    assert structural.status_code == 200
    assert any(c["kind"] == "AMBIGUOUS" for c in structural.json()["conflicts"])

    pl_e = _pl(client, auth_header, store_id, "PL Emg")
    client.post(
        "/api/v1/schedules",
        json={
            "channel_id": ch,
            "playlist_id": pl_e,
            "name": "Emerg",
            "start_time": "08:00",
            "end_time": "18:00",
            "days_of_week": [0, 1, 2, 3, 4, 5, 6],
            "priority": "EMERGENCY",
        },
        headers=auth_header,
    )
    now = client.get(f"/api/v1/channels/{ch}/now", headers=auth_header).json()
    assert now["schedule"]["priority"] == "EMERGENCY"


def test_cross_store_playlist_and_layout_rejected(client, auth_header, seeded, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    from app.core.config import get_settings

    get_settings.cache_clear()
    store_id = seeded["store"].id
    db = seeded["db"]
    other = Company(name="Outra", external_code="UX9O")
    db.add(other)
    db.flush()
    other_store = Store(company_id=other.id, name="Loja Z")
    db.add(other_store)
    db.commit()

    foreign_pl = _pl(client, auth_header, other_store.id, "ForeignPL")
    ch = client.post(
        "/api/v1/channels",
        json={"store_id": store_id, "name": "Canal Iso", "default_playlist_id": foreign_pl},
        headers=auth_header,
    )
    assert ch.status_code == 422

    LayoutService(db).ensure_system_templates()
    foreign_tpl = LayoutTemplate(
        store_id=other_store.id,
        name="Tpl Outra",
        slug="outra_tpl",
        orientation="LANDSCAPE",
        is_system=False,
        active=True,
    )
    db.add(foreign_tpl)
    db.commit()

    ok_ch = client.post(
        "/api/v1/channels",
        json={"store_id": store_id, "name": "Canal Ok"},
        headers=auth_header,
    )
    assert ok_ch.status_code == 201
    bad_layout = client.patch(
        f"/api/v1/channels/{ok_ch.json()['id']}",
        json={"layout_template_id": foreign_tpl.id, "store_id": store_id},
        headers=auth_header,
    )
    assert bad_layout.status_code == 422


def test_delete_channel_blocked_by_display(client, auth_header, seeded):
    store_id = seeded["store"].id
    ch = client.post(
        "/api/v1/channels",
        json={"store_id": store_id, "name": "Canal Del"},
        headers=auth_header,
    ).json()
    db = seeded["db"]
    db.add(
        Display(
            store_id=store_id,
            name="TV Del",
            code="TV-DEL",
            token="tok-del-ux9",
            channel_id=ch["id"],
            active=True,
        )
    )
    db.commit()
    blocked = client.delete(
        f"/api/v1/channels/{ch['id']}",
        params={"store_id": store_id},
        headers=auth_header,
    )
    assert blocked.status_code == 409


def test_boundary_start_end_and_overnight(seeded):
    db = seeded["db"]
    pl = Playlist(store_id=seeded["store"].id, name="Bound PL")
    db.add(pl)
    db.flush()
    ch = Channel(store_id=seeded["store"].id, name="Bound")
    db.add(ch)
    db.flush()

    night = Schedule(
        channel_id=ch.id,
        playlist_id=pl.id,
        name="Night",
        start_time=time(22, 0),
        end_time=time(2, 0),
        days_of_week="0,1,2,3,4,5,6",
        priority="NORMAL",
        active=True,
    )
    day = Schedule(
        channel_id=ch.id,
        playlist_id=pl.id,
        name="Exact",
        start_time=time(8, 0),
        end_time=time(12, 0),
        days_of_week="0",
        priority="NORMAL",
        active=True,
    )
    db.add_all([night, day])
    db.commit()

    # Monday 23:00 matches overnight
    assert schedule_matches(night, datetime(2026, 11, 2, 23, 0)) is True
    # Monday 03:00 does not (after end)
    assert schedule_matches(night, datetime(2026, 11, 2, 3, 0)) is False
    # Tuesday 01:00 matches overnight into Tuesday (weekday still checked as Tuesday)
    assert schedule_matches(night, datetime(2026, 11, 3, 1, 0)) is True

    assert schedule_matches(day, datetime(2026, 11, 2, 8, 0)) is True
    assert schedule_matches(day, datetime(2026, 11, 2, 12, 0)) is True
    assert schedule_matches(day, datetime(2026, 11, 2, 12, 1)) is False

    # Service next_at / active_at share schedule_matches
    svc = ScheduleService(db)
    at = datetime(2026, 11, 2, 9, 0)
    active = svc.active_at(ch.id, at)
    assert active["schedule"]["name"] == "Exact"

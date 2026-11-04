"""UX-6C — Screen Override Engine tests."""

from datetime import timedelta
from unittest.mock import patch

from app.modules.queue.models.entities import Display, utcnow
from app.modules.signage.models import Channel, LayoutTemplate
from app.modules.signage.override_priority import OVERRIDE_PRIORITY, QUEUE_CALL_DURATION_SECONDS, priority_for
from app.modules.signage.override_service import ScreenOverrideService


def _display(seeded, *, token="display-ov-token", channel_id=None):
    db = seeded["db"]
    d = Display(
        store_id=seeded["store"].id,
        department_id=seeded["department"].id,
        queue_id=seeded["queue"].id,
        name="TV Override",
        code="TV-OV",
        token=token,
        channel_id=channel_id,
        audio_enabled=True,
        active=True,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def test_priority_mapping():
    assert priority_for("EMERGENCY") == 400
    assert priority_for("QUEUE_CALL") == 300
    assert priority_for("MANUAL") == 200
    assert priority_for("CAMPAIGN") == 100
    assert OVERRIDE_PRIORITY["EMERGENCY"] > OVERRIDE_PRIORITY["QUEUE_CALL"]


def test_create_admin_types_and_reject_queue_call(client, auth_header, seeded):
    store_id = seeded["store"].id
    for otype in ("MANUAL", "EMERGENCY", "CAMPAIGN"):
        r = client.post(
            "/api/v1/screen-overrides",
            json={
                "store_id": store_id,
                "override_type": otype,
                "target_scope": "STORE",
                "payload": {"title": f"T {otype}", "message": "msg"},
                "duration_seconds": 30,
            },
            headers=auth_header,
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["override_type"] == otype
        assert body["priority"] == OVERRIDE_PRIORITY[otype]
        assert body["cancelled_at"] is None

    bad = client.post(
        "/api/v1/screen-overrides",
        json={
            "store_id": store_id,
            "override_type": "QUEUE_CALL",
            "target_scope": "QUEUE",
            "target_id": seeded["queue"].id,
            "payload": {
                "ticket_number": "A1",
                "queue_id": seeded["queue"].id,
                "department_name": "X",
            },
            "duration_seconds": 7,
        },
        headers=auth_header,
    )
    assert bad.status_code == 422, bad.text


def test_target_validation_and_cross_store(client, auth_header, seeded, db_session):
    store_id = seeded["store"].id
    # QUEUE without target_id
    r = client.post(
        "/api/v1/screen-overrides",
        json={
            "store_id": store_id,
            "override_type": "MANUAL",
            "target_scope": "QUEUE",
            "payload": {"title": "x", "message": "y"},
            "duration_seconds": 10,
        },
        headers=auth_header,
    )
    assert r.status_code == 422

    # cross-store display
    from app.modules.org.models.entities import Company, Store

    other_co = Company(name="Other", external_code="OTH")
    db_session.add(other_co)
    db_session.flush()
    other_store = Store(company_id=other_co.id, name="Loja B")
    db_session.add(other_store)
    db_session.flush()
    foreign = Display(
        store_id=other_store.id,
        name="Foreign",
        code="TV-F",
        token="foreign-token",
        active=True,
    )
    db_session.add(foreign)
    db_session.commit()

    cross = client.post(
        "/api/v1/screen-overrides",
        json={
            "store_id": store_id,
            "override_type": "MANUAL",
            "target_scope": "DISPLAY",
            "target_id": foreign.id,
            "payload": {"title": "x", "message": "y"},
            "duration_seconds": 10,
        },
        headers=auth_header,
    )
    assert cross.status_code in (403, 400, 404), cross.text


def test_active_expired_cancelled_resolution(db_session, seeded):
    svc = ScreenOverrideService(db_session)
    store_id = seeded["store"].id
    display = _display(seeded, token="disp-active")

    active = svc.create(
        store_id=store_id,
        override_type="MANUAL",
        target_scope="STORE",
        payload={"title": "on", "message": "m"},
        duration_seconds=60,
    )
    expired = svc.create(
        store_id=store_id,
        override_type="CAMPAIGN",
        target_scope="STORE",
        payload={"title": "old", "message": "m"},
        starts_at=utcnow() - timedelta(minutes=10),
        expires_at=utcnow() - timedelta(minutes=5),
    )
    cancelled = svc.create(
        store_id=store_id,
        override_type="EMERGENCY",
        target_scope="STORE",
        payload={"title": "cancel", "message": "m"},
        duration_seconds=60,
    )
    svc.cancel(cancelled["id"])

    resolved = svc.resolve_active_for_display(display)
    ids = {o["id"] for o in resolved}
    assert active["id"] in ids
    assert expired["id"] not in ids
    assert cancelled["id"] not in ids


def test_dedupe_key(db_session, seeded):
    svc = ScreenOverrideService(db_session)
    a = svc.create(
        store_id=seeded["store"].id,
        override_type="MANUAL",
        target_scope="STORE",
        payload={"title": "a", "message": "m"},
        duration_seconds=30,
        dedupe_key="dedupe-1",
    )
    b = svc.create(
        store_id=seeded["store"].id,
        override_type="MANUAL",
        target_scope="STORE",
        payload={"title": "b", "message": "m"},
        duration_seconds=30,
        dedupe_key="dedupe-1",
    )
    assert a["id"] == b["id"]


def test_target_scopes_display_queue_channel(db_session, seeded):
    svc = ScreenOverrideService(db_session)
    store_id = seeded["store"].id
    ch = Channel(store_id=store_id, name="Ch OV", layout="queue_media_split")
    db_session.add(ch)
    db_session.commit()
    display = _display(seeded, token="disp-scopes", channel_id=ch.id)

    for scope, tid in (
        ("STORE", None),
        ("QUEUE", seeded["queue"].id),
        ("DISPLAY", display.id),
        ("CHANNEL", ch.id),
    ):
        row = svc.create(
            store_id=store_id,
            override_type="MANUAL",
            target_scope=scope,
            target_id=tid,
            payload={"title": scope, "message": "m"},
            duration_seconds=20,
        )
        assert row["target_scope"] == scope

    matched = svc.resolve_active_for_display(display)
    assert len(matched) >= 4


def test_preemption_order(db_session, seeded):
    svc = ScreenOverrideService(db_session)
    display = _display(seeded, token="disp-preempt")
    store_id = seeded["store"].id
    camp = svc.create(
        store_id=store_id,
        override_type="CAMPAIGN",
        target_scope="STORE",
        payload={"title": "c", "message": "m"},
        duration_seconds=60,
    )
    manual = svc.create(
        store_id=store_id,
        override_type="MANUAL",
        target_scope="STORE",
        payload={"title": "m", "message": "m"},
        duration_seconds=60,
    )
    call = svc.create(
        store_id=store_id,
        override_type="QUEUE_CALL",
        target_scope="QUEUE",
        target_id=seeded["queue"].id,
        payload={
            "ticket_number": "A10",
            "queue_id": seeded["queue"].id,
            "department_name": "Açougue",
        },
        duration_seconds=QUEUE_CALL_DURATION_SECONDS,
        allow_queue_call=True,
        publish_ws=False,
    )
    emergency = svc.create(
        store_id=store_id,
        override_type="EMERGENCY",
        target_scope="STORE",
        payload={"title": "e", "message": "m"},
        duration_seconds=60,
    )
    ordered = svc.resolve_active_for_display(display)
    assert ordered[0]["id"] == emergency["id"]
    assert ordered[0]["priority"] == 400
    # cancel emergency → QUEUE_CALL wins
    svc.cancel(emergency["id"])
    ordered2 = svc.resolve_active_for_display(display)
    assert ordered2[0]["id"] == call["id"]
    svc.cancel(call["id"])
    ordered3 = svc.resolve_active_for_display(display)
    assert ordered3[0]["id"] == manual["id"]
    assert camp["id"] in {o["id"] for o in ordered3}


def test_queue_call_and_recall_integration(client, auth_header, seeded):
    qid = seeded["queue"].id
    display = _display(seeded, token="disp-call")

    client.post(
        f"/api/v1/queues/{qid}/tickets",
        json={"type": "NORMAL"},
        headers={**auth_header, "Idempotency-Key": "ov-t1"},
    )
    called = client.post(
        f"/api/v1/queues/{qid}/next",
        json={"terminal_id": "T-OV", "auto_start": True},
        headers={**auth_header, "Idempotency-Key": "ov-next"},
    )
    assert called.status_code == 200, called.text
    ticket_id = called.json()["id"]

    listed = client.get(
        "/api/v1/screen-overrides",
        params={"store_id": seeded["store"].id, "active": True, "override_type": "QUEUE_CALL"},
        headers=auth_header,
    )
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) >= 1
    assert rows[0]["override_type"] == "QUEUE_CALL"
    assert rows[0]["payload"]["ticket_number"] == called.json()["number"]

    cfg = client.get("/api/v1/player/config", headers={"X-Display-Token": "disp-call"})
    assert cfg.status_code == 200
    assert "active_overrides" in cfg.json()
    assert isinstance(cfg.json()["active_overrides"], list)
    assert any(o["override_type"] == "QUEUE_CALL" for o in cfg.json()["active_overrides"])

    recall = client.post(
        f"/api/v1/tickets/{ticket_id}/recall",
        json={"terminal_id": "T-OV"},
        headers=auth_header,
    )
    assert recall.status_code == 200, recall.text
    listed2 = client.get(
        "/api/v1/screen-overrides",
        params={"store_id": seeded["store"].id, "override_type": "QUEUE_CALL"},
        headers=auth_header,
    )
    assert len(listed2.json()) >= 2


def test_core_queue_survives_override_failure(client, auth_header, seeded):
    """Falha na camada Indoor não invalida ticket.called."""
    qid = seeded["queue"].id
    client.post(
        f"/api/v1/queues/{qid}/tickets",
        json={"type": "NORMAL"},
        headers={**auth_header, "Idempotency-Key": "ov-safe-t"},
    )
    with patch(
        "app.modules.signage.override_service.ScreenOverrideService.create",
        side_effect=RuntimeError("simulated override persist failure"),
    ):
        r = client.post(
            f"/api/v1/queues/{qid}/next",
            json={"terminal_id": "T-SAFE", "auto_start": True},
            headers={**auth_header, "Idempotency-Key": "ov-safe-next"},
        )
    assert r.status_code == 200, r.text
    assert r.json().get("number")
    assert r.json().get("id")


def test_cancel_soft_and_list_filters(client, auth_header, seeded):
    store_id = seeded["store"].id
    created = client.post(
        "/api/v1/screen-overrides",
        json={
            "store_id": store_id,
            "override_type": "EMERGENCY",
            "target_scope": "STORE",
            "payload": {"title": "Evacuar", "message": "Saída"},
            "duration_seconds": 120,
        },
        headers=auth_header,
    )
    assert created.status_code == 201
    oid = created.json()["id"]
    cancelled = client.post(f"/api/v1/screen-overrides/{oid}/cancel", headers=auth_header)
    assert cancelled.status_code == 200
    assert cancelled.json()["cancelled_at"] is not None

    active = client.get(
        "/api/v1/screen-overrides",
        params={"store_id": store_id, "active": True},
        headers=auth_header,
    )
    assert all(o["id"] != oid for o in active.json())


def test_ux6b_global_slug_uniqueness_preflight(db_session):
    """Pre-flight UX-6B: partial unique already seeded via LayoutService / migration."""
    from app.modules.signage.layout_service import LayoutService

    LayoutService(db_session).ensure_system_templates()
    from sqlalchemy import select

    systems = list(
        db_session.scalars(select(LayoutTemplate).where(LayoutTemplate.is_system.is_(True))).all()
    )
    slugs = [t.slug for t in systems]
    assert len(slugs) == len(set(slugs))
    assert "fullscreen_media" in slugs

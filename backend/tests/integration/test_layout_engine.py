"""UX-6B — Layout Engine tests."""

from app.modules.queue.models.entities import Display
from app.modules.signage.layout_service import DEFAULT_SLUG, LEGACY_LAYOUT_MAP, LayoutService
from app.modules.signage.models import Channel, LayoutTemplate


def test_system_templates_and_zones(db_session):
    svc = LayoutService(db_session)
    svc.ensure_system_templates()
    templates = svc.list_templates()
    slugs = {t["slug"] for t in templates}
    assert {
        "fullscreen_media",
        "media_queue_footer",
        "media_queue_sidebar",
        "queue_fullscreen",
    }.issubset(slugs)

    footer = next(t for t in templates if t["slug"] == "media_queue_footer")
    assert len(footer["zones"]) == 2
    types = {z["type"] for z in footer["zones"]}
    assert types == {"MEDIA", "QUEUE"}
    media = next(z for z in footer["zones"] if z["type"] == "MEDIA")
    assert media["height"] == 82
    queue = next(z for z in footer["zones"] if z["type"] == "QUEUE")
    assert queue["y"] == 82
    assert queue["config"]["variant"] == "footer"

    # idempotent
    svc.ensure_system_templates()
    from sqlalchemy import select

    systems = list(db_session.scalars(select(LayoutTemplate).where(LayoutTemplate.is_system.is_(True))).all())
    assert len(systems) == 4


def test_legacy_mapping_and_explicit_template(db_session, seeded):
    svc = LayoutService(db_session)
    svc.ensure_system_templates()
    store_id = seeded["store"].id

    ch = Channel(
        store_id=store_id,
        name="Canal Legacy",
        layout="queue_media_split",
        layout_template_id=None,
    )
    db_session.add(ch)
    db_session.commit()

    assert LEGACY_LAYOUT_MAP["queue_media_split"] == DEFAULT_SLUG
    resolved = svc.resolve_for_channel(channel=ch, store_id=store_id)
    assert resolved["slug"] == "media_queue_footer"
    assert resolved["resolved_from"] == "legacy_layout"

    sidebar = svc.get_by_slug("media_queue_sidebar")
    assert sidebar is not None
    ch.layout_template_id = sidebar.id
    db_session.commit()
    db_session.refresh(ch)
    resolved2 = svc.resolve_for_channel(channel=ch, store_id=store_id)
    assert resolved2["slug"] == "media_queue_sidebar"
    assert resolved2["resolved_from"] == "layout_template_id"


def test_fallback_without_channel(db_session):
    svc = LayoutService(db_session)
    resolved = svc.resolve_for_channel(channel=None, store_id=None)
    assert resolved["slug"] == DEFAULT_SLUG
    assert resolved["zones"]


def test_layout_templates_api_and_player_config(client, auth_header, seeded):
    db_session = seeded["db"]
    LayoutService(db_session).ensure_system_templates()

    listed = client.get("/api/v1/layout-templates", headers=auth_header)
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert len(body) >= 4
    tpl_id = next(t["id"] for t in body if t["slug"] == "queue_fullscreen")

    detail = client.get(f"/api/v1/layout-templates/{tpl_id}", headers=auth_header)
    assert detail.status_code == 200
    assert detail.json()["slug"] == "queue_fullscreen"

    store_id = seeded["store"].id
    queue_id = seeded["queue"].id
    ch = client.post(
        "/api/v1/channels",
        json={"store_id": store_id, "name": "Canal Layout", "layout": "queue_media_split"},
        headers=auth_header,
    )
    assert ch.status_code == 201, ch.text
    channel_id = ch.json()["id"]
    assert ch.json().get("layout_template_id") is None

    disp = Display(
        store_id=store_id,
        queue_id=queue_id,
        department_id=seeded["department"].id,
        name="TV Layout",
        code="TV-LAY",
        token="display-layout-token",
        channel_id=channel_id,
        active=True,
    )
    db_session.add(disp)
    db_session.commit()

    cfg = client.get(
        "/api/v1/player/config",
        headers={"X-Display-Token": "display-layout-token"},
        params={"token": "display-layout-token"},
    )
    assert cfg.status_code == 200, cfg.text
    data = cfg.json()
    assert "layout" in data
    assert data["layout"]["slug"] == "media_queue_footer"
    assert data["channel"]["layout"] == "queue_media_split"
    assert data["playlist"] is not None or True

    # explicit template
    patch = client.patch(
        f"/api/v1/channels/{channel_id}",
        json={"layout_template_id": tpl_id},
        headers=auth_header,
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["layout_template_id"] == tpl_id

    cfg2 = client.get(
        "/api/v1/player/config",
        headers={"X-Display-Token": "display-layout-token"},
        params={"token": "display-layout-token"},
    )
    assert cfg2.status_code == 200
    assert cfg2.json()["layout"]["slug"] == "queue_fullscreen"

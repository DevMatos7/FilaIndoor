from app.core.config import get_settings
from app.modules.toledo.providers.toledo import ToledoProvider
from app.modules.queue.models.entities import Ticket


def test_toledo_provider_skips_when_disabled():
    p = ToledoProvider(enabled=False, mode="TOLEDO_DISPLAY", confirmed={"player_push": True}, mock=False)
    r = p.push_ticket_to_player(ticket_number="A1")
    assert r.skipped is True
    assert r.ok is True
    assert p.fetch_history() == []


def test_toledo_provider_mock_push_and_history(monkeypatch):
    monkeypatch.setenv("TOLEDO_ENABLED", "true")
    monkeypatch.setenv("TOLEDO_MODE", "TOLEDO_FULL")
    monkeypatch.setenv("TOLEDO_MOCK", "true")
    get_settings.cache_clear()

    p = ToledoProvider(
        enabled=True,
        mode="TOLEDO_FULL",
        mock=True,
        confirmed={"player_push": True, "history": True},
    )
    push = p.push_ticket_to_player(ticket_number="A010", counter="2")
    assert push.ok and not push.skipped
    hist = p.fetch_history()
    assert len(hist) >= 1
    get_settings.cache_clear()


def test_adapter_api_and_native_call_unaffected(client, auth_header, seeded, monkeypatch):
    monkeypatch.setenv("TOLEDO_ENABLED", "false")
    get_settings.cache_clear()

    st = client.get("/api/v1/toledo/status")
    assert st.status_code == 200
    assert st.json()["adapter_implemented"] is True
    assert st.json()["effective_mode"] == "NATIVE"

    info = client.get("/api/v1/toledo/adapter", headers=auth_header)
    assert info.status_code == 200
    assert info.json()["native"]["queue_source_of_truth"] is True
    assert info.json()["toledo"]["never_blocks_native"] is True

    push = client.post(
        "/api/v1/toledo/adapter/test-push",
        json={"ticket_number": "A001"},
        headers=auth_header,
    )
    assert push.status_code == 200
    assert push.json()["skipped"] is True  # flag off

    # chamada nativa continua funcionando
    issued = client.post(
        f"/api/v1/queues/{seeded['queue'].id}/tickets",
        json={"type": "NORMAL"},
        headers=auth_header,
    )
    assert issued.status_code == 201, issued.text
    nxt = client.post(
        f"/api/v1/queues/{seeded['queue'].id}/next",
        json={},
        headers=auth_header,
    )
    assert nxt.status_code == 200, nxt.text
    assert nxt.json().get("number") or nxt.json().get("display_number")

    # ticket existe no banco nativo
    tid = nxt.json()["id"]
    assert seeded["db"].get(Ticket, tid) is not None
    get_settings.cache_clear()


def test_mock_adapter_endpoints(client, auth_header, monkeypatch):
    monkeypatch.setenv("TOLEDO_ENABLED", "true")
    monkeypatch.setenv("TOLEDO_MODE", "TOLEDO_FULL")
    monkeypatch.setenv("TOLEDO_MOCK", "true")
    get_settings.cache_clear()

    # marcar discovery com api
    client.put(
        "/api/v1/toledo/discovery",
        json={"api_enabled": True, "docs_compared": True, "confirmed_capabilities": {"player_push": True, "history": True}},
        headers=auth_header,
    )

    push = client.post(
        "/api/v1/toledo/adapter/test-push",
        json={"ticket_number": "P001"},
        headers=auth_header,
    )
    assert push.status_code == 200, push.text
    assert push.json()["ok"] is True
    assert push.json()["skipped"] is False

    hist = client.post("/api/v1/toledo/adapter/sync-history", headers=auth_header)
    assert hist.status_code == 200
    assert hist.json()["ok"] is True
    assert hist.json()["count"] >= 1
    get_settings.cache_clear()

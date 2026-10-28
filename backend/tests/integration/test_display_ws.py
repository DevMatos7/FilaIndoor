import asyncio

from app.modules.queue.models.entities import Display
from app.modules.realtime.hub import hub


def test_player_config(client, seeded):
    db = seeded["db"]
    display = Display(
        store_id=seeded["store"].id,
        department_id=seeded["department"].id,
        queue_id=seeded["queue"].id,
        name="TV Teste",
        code="TV-T",
        token="display-test-token",
        audio_enabled=True,
    )
    db.add(display)
    db.commit()

    r = client.get(
        "/api/v1/player/config",
        headers={"X-Display-Token": "display-test-token"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["display"]["audio_enabled"] is True
    assert body["store_id"] == seeded["store"].id
    assert body["ws_path"].endswith(seeded["store"].id)


def test_ws_broadcast_and_dedup_payload(seeded):
    store_id = seeded["store"].id
    received: list[dict] = []

    class FakeWs:
        async def send_json(self, payload):
            received.append(payload)

    # conecta fake room
    hub._rooms[store_id] = {FakeWs()}  # type: ignore[arg-type]

    asyncio.run(hub.broadcast(store_id, "ticket.called", {"ticket": "A001", "department": "Açougue"}))
    assert len(received) == 1
    assert received[0]["event"] == "ticket.called"
    assert "event_id" in received[0]
    hub._rooms.pop(store_id, None)


def test_call_next_publishes_without_error(client, auth_header, seeded):
    qid = seeded["queue"].id
    client.post(
        f"/api/v1/queues/{qid}/tickets",
        json={"type": "NORMAL"},
        headers={**auth_header, "Idempotency-Key": "ws-t1"},
    )
    r = client.post(
        f"/api/v1/queues/{qid}/next",
        json={"terminal_id": "T-WS", "auto_start": True},
        headers={**auth_header, "Idempotency-Key": "ws-next"},
    )
    assert r.status_code == 200, r.text

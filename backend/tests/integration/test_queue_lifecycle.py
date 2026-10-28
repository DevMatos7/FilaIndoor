import pytest

from app.core.exceptions import InvalidTransitionError
from app.modules.queue.services.queue_service import QueueService


def test_create_ticket_and_lifecycle(seeded):
    service: QueueService = seeded["service"]
    queue_id = seeded["queue"].id

    t1 = service.create_ticket(queue_id, ticket_type="NORMAL")
    assert t1["number"] == "A001"
    assert t1["status"] == "WAITING"

    t2 = service.create_ticket(queue_id, ticket_type="NORMAL")
    assert t2["number"] == "A002"

    p1 = service.create_ticket(queue_id, ticket_type="PRIORITY")
    assert p1["number"] == "P001"

    called = service.call_next(queue_id, terminal_id="T1", operator_id="op1")
    assert called["number"] == "A001"
    assert called["status"] == "CALLED"

    started = service.start(called["id"], operator_id="op1", terminal_id="T1")
    assert started["status"] == "SERVING"

    done = service.complete(called["id"], operator_id="op1", terminal_id="T1")
    assert done["status"] == "COMPLETED"

    detail = service.ticket_detail(called["id"])
    types = [e["event_type"] for e in detail["events"]]
    assert types == [
        "TICKET_CREATED",
        "TICKET_CALLED",
        "SERVICE_STARTED",
        "SERVICE_COMPLETED",
    ]


def test_weighted_call_order(seeded):
    service: QueueService = seeded["service"]
    qid = seeded["queue"].id
    for _ in range(4):
        service.create_ticket(qid, ticket_type="NORMAL")
    service.create_ticket(qid, ticket_type="PRIORITY")

    order = []
    for i in range(5):
        ticket = service.call_next(qid, terminal_id=f"T{i}", operator_id="op", auto_complete_current=False)
        # finalize previous pattern: complete current before next without auto
        if ticket["status"] == "CALLED":
            service.complete(ticket["id"], terminal_id=f"T{i}")
        order.append(ticket["number"])
    assert order == ["A001", "A002", "A003", "P001", "A004"]


def test_invalid_transition(seeded):
    service: QueueService = seeded["service"]
    qid = seeded["queue"].id
    t = service.create_ticket(qid, ticket_type="NORMAL")
    with pytest.raises(InvalidTransitionError):
        service.complete(t["id"])


def test_no_show_and_cancel(seeded):
    service: QueueService = seeded["service"]
    qid = seeded["queue"].id
    a = service.create_ticket(qid, ticket_type="NORMAL")
    b = service.create_ticket(qid, ticket_type="NORMAL")
    called = service.call_next(qid, terminal_id="T1", auto_complete_current=False)
    assert called["id"] == a["id"]
    noshow = service.no_show(called["id"], terminal_id="T1")
    assert noshow["status"] == "NO_SHOW"
    cancelled = service.cancel(b["id"])
    assert cancelled["status"] == "CANCELLED"


def test_idempotency_create(seeded):
    service: QueueService = seeded["service"]
    qid = seeded["queue"].id
    first = service.create_ticket(qid, ticket_type="NORMAL", idempotency_key="k1")
    second = service.create_ticket(qid, ticket_type="NORMAL", idempotency_key="k1")
    assert first["id"] == second["id"]
    third = service.create_ticket(qid, ticket_type="NORMAL", idempotency_key="k2")
    assert third["id"] != first["id"]


def test_api_status_and_waiting(client, auth_header, seeded):
    qid = seeded["queue"].id
    r = client.post(
        f"/api/v1/queues/{qid}/tickets",
        json={"type": "NORMAL", "source": "KIOSK"},
        headers={**auth_header, "Idempotency-Key": "api-1"},
    )
    assert r.status_code == 201, r.text
    waiting = client.get(f"/api/v1/queues/{qid}/waiting", headers=auth_header)
    assert waiting.status_code == 200
    assert len(waiting.json()) == 1
    status = client.get(f"/api/v1/queues/{qid}/status", headers=auth_header)
    assert status.status_code == 200
    assert status.json()["waiting_count"] == 1

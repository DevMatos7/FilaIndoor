from datetime import date


def test_analytics_summary_empty_day(client, auth_header, seeded):
    r = client.get(
        "/api/v1/analytics/summary",
        params={"day": "2099-01-01", "queue_id": seeded["queue"].id},
        headers=auth_header,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kpis"]["issued"] == 0
    assert body["kpis"]["completed"] == 0
    assert len(body["hourly"]) == 24


def test_analytics_summary_after_flow(client, auth_header, seeded):
    qid = seeded["queue"].id
    headers = {**auth_header, "Idempotency-Key": "an-1"}
    created = client.post(
        f"/api/v1/queues/{qid}/tickets",
        json={"type": "NORMAL"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    ticket_id = created.json()["id"]

    client.post(
        f"/api/v1/queues/{qid}/tickets",
        json={"type": "PRIORITY"},
        headers={**auth_header, "Idempotency-Key": "an-2"},
    )

    nxt = client.post(
        f"/api/v1/queues/{qid}/next",
        json={"terminal_id": "T-AN", "auto_start": True},
        headers={**auth_header, "Idempotency-Key": "an-next"},
    )
    assert nxt.status_code == 200, nxt.text

    client.post(
        f"/api/v1/tickets/{ticket_id}/complete",
        json={"terminal_id": "T-AN"},
        headers=auth_header,
    )

    today = date.today().isoformat()
    r = client.get(
        "/api/v1/analytics/summary",
        params={"day": today, "queue_id": qid},
        headers=auth_header,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kpis"]["issued"] >= 2
    assert body["kpis"]["completed"] >= 1
    assert body["kpis"]["waiting"] >= 1
    assert body["by_type"].get("NORMAL", 0) >= 1
    assert body["kpis"]["wait"]["avg_seconds"] is not None
    assert body["kpis"]["service"]["avg_seconds"] is not None
    assert sum(h["issued"] for h in body["hourly"]) == body["kpis"]["issued"]
    assert body["sla"]["green"] + body["sla"]["yellow"] + body["sla"]["red"] + body["sla"]["unknown"] == body[
        "kpis"
    ]["issued"]

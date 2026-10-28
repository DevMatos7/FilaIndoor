def test_real_plus_preview_issue_track_checkin_notify(client, auth_header, seeded):
    queue_id = seeded["queue"].id

    preview = client.get(f"/api/v1/real-plus/queues/{queue_id}/preview")
    assert preview.status_code == 200, preview.text
    assert "waiting_count" in preview.json()

    issue = client.post(
        f"/api/v1/real-plus/queues/{queue_id}/tickets",
        json={"type": "NORMAL", "notify_when_ahead": 5, "customer_label": "Cliente App"},
        headers={"Idempotency-Key": "rp-1"},
    )
    assert issue.status_code == 201, issue.text
    body = issue.json()
    token = body["tracking_token"]
    assert body["ticket"]["number"]
    # sozinho na fila → people_ahead 0 dispara aviso de proximidade (APPROACHING)
    assert body["presence_status"] in {"WAITING_REMOTE", "APPROACHING"}
    assert len(body["notifications"]) >= 1

    track = client.get(f"/api/v1/real-plus/track/{token}")
    assert track.status_code == 200
    assert track.json()["ticket"]["people_ahead"] >= 0

    sub = client.post(f"/api/v1/real-plus/track/{token}/subscribe", json={"endpoint": "stub://test"})
    assert sub.status_code == 200
    assert sub.json()["ok"] is True

    check = client.post(f"/api/v1/real-plus/track/{token}/check-in")
    assert check.status_code == 200, check.text
    assert check.json()["presence_status"] == "CHECKED_IN"
    assert check.json()["checked_in_at"]

    listed = client.get("/api/v1/real-plus/virtual-tickets", params={"queue_id": queue_id}, headers=auth_header)
    assert listed.status_code == 200
    assert any(r["tracking_token"] == token for r in listed.json())


def test_real_plus_disabled(client, seeded, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("REAL_PLUS_ENABLED", "false")
    get_settings.cache_clear()
    resp = client.get(f"/api/v1/real-plus/queues/{seeded['queue'].id}/preview")
    assert resp.status_code == 403
    get_settings.cache_clear()

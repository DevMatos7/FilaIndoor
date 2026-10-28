def test_edge_health_outbox_sync_idempotent(client, auth_header, seeded):
    store_id = seeded["store"].id

    health = client.get("/api/v1/edge/health")
    assert health.status_code == 200
    assert health.json()["mode"] == "edge"
    assert health.json()["offline_capable"] is True

    event_id = "evt-edge-1"
    push = client.post(
        "/api/v1/edge/outbox",
        json={
            "events": [
                {
                    "event_id": event_id,
                    "store_id": store_id,
                    "event_type": "TELEMETRY",
                    "payload": {"free_storage_mb": 100},
                    "origin_device": "tv-1",
                }
            ]
        },
    )
    assert push.status_code == 200, push.text
    assert push.json()["accepted"] == 1
    assert push.json()["events"][0]["deduplicated"] is False

    again = client.post(
        "/api/v1/edge/outbox",
        json={
            "events": [
                {
                    "event_id": event_id,
                    "store_id": store_id,
                    "event_type": "TELEMETRY",
                    "payload": {"free_storage_mb": 100},
                }
            ]
        },
    )
    assert again.status_code == 200
    assert again.json()["events"][0]["deduplicated"] is True

    status = client.get("/api/v1/edge/sync/status", params={"store_id": store_id}, headers=auth_header)
    assert status.status_code == 200
    assert status.json()["pending"] >= 1

    flush = client.post("/api/v1/edge/sync", params={"store_id": store_id}, headers=auth_header)
    assert flush.status_code == 200, flush.text
    assert flush.json()["synced"] >= 1

    status2 = client.get("/api/v1/edge/sync/status", params={"store_id": store_id}, headers=auth_header)
    assert status2.json()["pending"] == 0
    assert status2.json()["synced"] >= 1


def test_edge_snapshot_and_kiosk_mirrors_outbox(client, auth_header, seeded):
    store_id = seeded["store"].id
    queue_id = seeded["queue"].id
    kiosk_token = seeded["kiosk_token"]

    snap = client.get("/api/v1/edge/snapshot", params={"store_id": store_id}, headers=auth_header)
    assert snap.status_code == 200, snap.text
    body = snap.json()
    assert body["store_id"] == store_id
    assert any(q["id"] == queue_id for q in body["queues"])

    st = client.get(f"/api/v1/kiosk/{queue_id}/status", headers={"X-Kiosk-Token": kiosk_token})
    assert st.status_code == 200
    assert st.json()["store_id"] == store_id
    assert st.json()["edge_cache"] is True

    issue = client.post(
        f"/api/v1/kiosk/{queue_id}/tickets",
        json={"type": "NORMAL"},
        headers={"X-Kiosk-Token": kiosk_token, "Idempotency-Key": "edge-kiosk-1"},
    )
    assert issue.status_code == 201, issue.text

    outbox = client.get(
        "/api/v1/edge/outbox",
        params={"store_id": store_id, "sync_status": "PENDING"},
        headers=auth_header,
    )
    assert outbox.status_code == 200
    types = [e["event_type"] for e in outbox.json()]
    assert "TICKET_ISSUED" in types

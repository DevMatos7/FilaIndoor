from app.modules.queue.models.entities import Display, Terminal


def test_queue_settings_get_and_patch(client, auth_header, seeded):
    qid = seeded["queue"].id
    r = client.get(f"/api/v1/queues/{qid}/settings", headers=auth_header)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == qid
    assert body["priority_rule"]["normal_weight"] == 3
    assert body["kiosk_enabled"] is True

    patch = client.patch(
        f"/api/v1/queues/{qid}",
        json={
            "name": "Fila Açougue Atualizada",
            "normal_weight": 2,
            "priority_weight": 1,
            "priority_max_wait_seconds": 300,
            "department_display_name": "Açougue VIP",
        },
        headers=auth_header,
    )
    assert patch.status_code == 200, patch.text
    updated = patch.json()
    assert updated["name"] == "Fila Açougue Atualizada"
    assert updated["priority_rule"]["normal_weight"] == 2
    assert updated["priority_rule"]["priority_max_wait_seconds"] == 300
    assert updated["department_display_name"] == "Açougue VIP"


def test_history_list_filters_and_timings(client, auth_header, seeded):
    qid = seeded["queue"].id
    headers = {**auth_header, "Idempotency-Key": "hist-1"}
    created = client.post(
        f"/api/v1/queues/{qid}/tickets",
        json={"type": "NORMAL"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    ticket_id = created.json()["id"]
    number = created.json()["number"]

    client.post(
        f"/api/v1/queues/{qid}/next",
        json={"terminal_id": "T-HIST", "auto_start": True},
        headers={**auth_header, "Idempotency-Key": "hist-next"},
    )
    client.post(
        f"/api/v1/tickets/{ticket_id}/complete",
        json={"terminal_id": "T-HIST"},
        headers=auth_header,
    )

    hist = client.get(
        "/api/v1/tickets",
        params={"queue_id": qid, "status": "COMPLETED", "search": number},
        headers=auth_header,
    )
    assert hist.status_code == 200, hist.text
    payload = hist.json()
    assert payload["total"] >= 1
    assert any(i["id"] == ticket_id for i in payload["items"])
    item = next(i for i in payload["items"] if i["id"] == ticket_id)
    assert item["status"] == "COMPLETED"
    assert "wait_seconds" in item

    detail = client.get(f"/api/v1/tickets/{ticket_id}", headers=auth_header)
    assert detail.status_code == 200
    body = detail.json()
    assert "timings" in body
    assert body["timings"]["wait_seconds"] is not None
    assert len(body["events"]) >= 2


def test_devices_overview_and_patch(client, auth_header, seeded):
    db = seeded["db"]
    terminal = Terminal(department_id=seeded["department"].id, name="Balcão Hist", code="TH1")
    display = Display(
        store_id=seeded["store"].id,
        department_id=seeded["department"].id,
        queue_id=seeded["queue"].id,
        name="TV Hist",
        code="TV-H",
        token="display-hist-token",
        audio_enabled=True,
    )
    db.add(terminal)
    db.add(display)
    db.commit()
    db.refresh(terminal)
    db.refresh(display)

    overview = client.get("/api/v1/devices/overview", headers=auth_header)
    assert overview.status_code == 200, overview.text
    data = overview.json()
    assert any(t["id"] == terminal.id for t in data["terminals"])
    assert any(d["id"] == display.id for d in data["displays"])

    patched_display = client.patch(
        f"/api/v1/displays/{display.id}",
        json={"audio_enabled": False},
        headers=auth_header,
    )
    assert patched_display.status_code == 200, patched_display.text
    assert patched_display.json()["audio_enabled"] is False

    patched_terminal = client.patch(
        f"/api/v1/terminals/{terminal.id}",
        json={"active": False},
        headers=auth_header,
    )
    assert patched_terminal.status_code == 200, patched_terminal.text
    assert patched_terminal.json()["active"] is False

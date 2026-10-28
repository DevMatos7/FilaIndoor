from sqlalchemy import select

from app.modules.printing.providers.mock import MockPrinter
from app.modules.queue.models.entities import PrintJob, Ticket


def test_kiosk_issue_prints_and_keeps_ticket(client, seeded):
    MockPrinter.clear()
    qid = seeded["queue"].id
    token = seeded["kiosk_token"]

    r = client.post(
        f"/api/v1/kiosk/{qid}/tickets",
        json={"type": "NORMAL", "source": "KIOSK"},
        headers={
            "X-Kiosk-Token": token,
            "Idempotency-Key": "totem-1",
            "X-Print-Provider": "mock",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["ticket"]["number"].startswith("A")
    assert body["print"]["ok"] is True
    assert len(MockPrinter.last_jobs) == 1

    # senha permanece mesmo após "impressão"
    db = seeded["db"]
    ticket = db.get(Ticket, body["ticket"]["id"])
    assert ticket is not None
    assert ticket.status == "WAITING"


def test_kiosk_printer_fail_does_not_duplicate(client, seeded):
    qid = seeded["queue"].id
    token = seeded["kiosk_token"]

    r = client.post(
        f"/api/v1/kiosk/{qid}/tickets",
        json={"type": "PRIORITY", "source": "KIOSK"},
        headers={
            "X-Kiosk-Token": token,
            "Idempotency-Key": "totem-fail-1",
            "X-Print-Provider": "fail",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["ticket"]["number"].startswith("P")
    assert body["print"]["ok"] is False

    # mesma chave idempotente: mesma senha, não cria outra
    r2 = client.post(
        f"/api/v1/kiosk/{qid}/tickets",
        json={"type": "PRIORITY", "source": "KIOSK"},
        headers={
            "X-Kiosk-Token": token,
            "Idempotency-Key": "totem-fail-1",
            "X-Print-Provider": "fail",
        },
    )
    assert r2.status_code == 201
    assert r2.json()["ticket"]["id"] == body["ticket"]["id"]

    db = seeded["db"]
    jobs = db.scalars(select(PrintJob).where(PrintJob.ticket_id == body["ticket"]["id"])).all()
    assert len(jobs) >= 1
    assert any(j.status == "FAILED" for j in jobs)


def test_kiosk_rejects_bad_token(client, seeded):
    qid = seeded["queue"].id
    r = client.post(
        f"/api/v1/kiosk/{qid}/tickets",
        json={"type": "NORMAL"},
        headers={"X-Kiosk-Token": "wrong"},
    )
    assert r.status_code == 403


def test_kiosk_status(client, seeded):
    qid = seeded["queue"].id
    r = client.get(
        f"/api/v1/kiosk/{qid}/status",
        headers={"X-Kiosk-Token": seeded["kiosk_token"]},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Fila Açougue"
    assert r.json()["department_name"] == "Açougue"


def test_double_touch_idempotency(client, seeded):
    qid = seeded["queue"].id
    headers = {
        "X-Kiosk-Token": seeded["kiosk_token"],
        "Idempotency-Key": "double-tap",
        "X-Print-Provider": "mock",
    }
    a = client.post(f"/api/v1/kiosk/{qid}/tickets", json={"type": "NORMAL"}, headers=headers)
    b = client.post(f"/api/v1/kiosk/{qid}/tickets", json={"type": "NORMAL"}, headers=headers)
    assert a.status_code == 201 and b.status_code == 201
    assert a.json()["ticket"]["id"] == b.json()["ticket"]["id"]
    assert a.json()["ticket"]["number"] == b.json()["ticket"]["number"]

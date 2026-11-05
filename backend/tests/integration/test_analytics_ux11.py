"""UX-11 — Analytics 2.0: P90, cohorts, isolation, aggregation."""

from datetime import date, datetime, timedelta

from app.modules.analytics.service import _percentile
from app.modules.org.models.entities import Company, Department, Store
from app.modules.queue.models.entities import Queue, Ticket
from app.modules.queue.models.enums import TicketStatus, TicketType


def test_percentile_deterministic():
    # 1..10 → P90 = 9.1 with linear interpolation (index 0.9*9=8.1 → 9 + 0.1*(10-9))
    vals = [float(x) for x in range(1, 11)]
    assert _percentile(vals, 0.9) == 9.1
    assert _percentile([], 0.9) is None
    assert _percentile([5.0], 0.9) == 5.0


def test_overview_p90_not_average_of_queue_p90s(client, auth_header, seeded):
    """P90 do escopo = percentil das observações individuais, não média dos P90s."""
    db = seeded["db"]
    store_id = seeded["store"].id
    q1 = seeded["queue"]
    # segunda fila na mesma loja
    q2 = Queue(
        department_id=seeded["department"].id,
        name="Padaria UX11",
        status="OPEN",
        normal_prefix="P",
        priority_prefix="PP",
    )
    db.add(q2)
    db.flush()

    day = date.today()
    start = datetime.combine(day, datetime.min.time())

    # Fila A: 2 tickets wait 100s, 200s → P90 baixo
    for i, wait in enumerate([100, 200]):
        t = Ticket(
            queue_id=q1.id,
            sequence_number=1000 + i,
            display_number=f"UA{i}",
            period_key=day.isoformat(),
            ticket_type=TicketType.NORMAL.value,
            status=TicketStatus.COMPLETED.value,
            issued_at=start + timedelta(hours=1, minutes=i),
            called_at=start + timedelta(hours=1, minutes=i, seconds=wait),
            service_started_at=start + timedelta(hours=1, minutes=i, seconds=wait),
            completed_at=start + timedelta(hours=1, minutes=i, seconds=wait + 30),
            terminal_id="T-A",
        )
        db.add(t)

    # Fila B: muitos tickets com waits altos 800..1200
    for i in range(20):
        wait = 800 + i * 20  # 800..1180
        t = Ticket(
            queue_id=q2.id,
            sequence_number=2000 + i,
            display_number=f"UB{i}",
            period_key=day.isoformat(),
            ticket_type=TicketType.NORMAL.value,
            status=TicketStatus.COMPLETED.value,
            issued_at=start + timedelta(hours=2, minutes=i),
            called_at=start + timedelta(hours=2, minutes=i, seconds=wait),
            service_started_at=start + timedelta(hours=2, minutes=i, seconds=wait),
            completed_at=start + timedelta(hours=2, minutes=i, seconds=wait + 40),
            terminal_id="T-B",
        )
        db.add(t)
    db.commit()

    r = client.get(
        "/api/v1/analytics/overview",
        params={"store_id": store_id, "from": day.isoformat(), "to": day.isoformat()},
        headers=auth_header,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # todas as waits individuais
    all_waits = [100.0, 200.0] + [float(800 + i * 20) for i in range(20)]
    expected_p90 = round(_percentile(sorted(all_waits), 0.9), 1)
    assert body["metrics"]["wait"]["p90_seconds"] == expected_p90

    # média dos P90 das filas seria diferente
    rows = {q["name"]: q for q in body["queues"]}
    p90s = [rows[q1.name]["wait_p90_seconds"], rows[q2.name]["wait_p90_seconds"]]
    avg_of_p90s = round(sum(p90s) / 2, 1)
    assert body["metrics"]["wait"]["p90_seconds"] != avg_of_p90s


def test_missing_timestamps_not_zero(client, auth_header, seeded):
    db = seeded["db"]
    store_id = seeded["store"].id
    qid = seeded["queue"].id
    day = date.today()
    start = datetime.combine(day, datetime.min.time())
    # ticket ainda waiting — sem wait_end
    db.add(
        Ticket(
            queue_id=qid,
            sequence_number=3001,
            display_number="UW1",
            period_key=day.isoformat(),
            ticket_type=TicketType.NORMAL.value,
            status=TicketStatus.WAITING.value,
            issued_at=start + timedelta(hours=3),
        )
    )
    # completed com service timestamps
    db.add(
        Ticket(
            queue_id=qid,
            sequence_number=3002,
            display_number="UC1",
            period_key=day.isoformat(),
            ticket_type=TicketType.NORMAL.value,
            status=TicketStatus.COMPLETED.value,
            issued_at=start + timedelta(hours=1),
            called_at=start + timedelta(hours=1, minutes=5),
            service_started_at=start + timedelta(hours=1, minutes=5),
            completed_at=start + timedelta(hours=1, minutes=10),
        )
    )
    # completed sem service_started → service avg não inclui zero
    db.add(
        Ticket(
            queue_id=qid,
            sequence_number=3003,
            display_number="UC2",
            period_key=day.isoformat(),
            ticket_type=TicketType.NORMAL.value,
            status=TicketStatus.COMPLETED.value,
            issued_at=start + timedelta(hours=2),
            called_at=start + timedelta(hours=2, minutes=2),
            completed_at=start + timedelta(hours=2, minutes=8),
            service_started_at=None,
        )
    )
    db.commit()

    body = client.get(
        "/api/v1/analytics/overview",
        params={"store_id": store_id, "from": day.isoformat(), "to": day.isoformat()},
        headers=auth_header,
    ).json()
    assert body["metrics"]["sla"]["unknown"] >= 1
    assert body["metrics"]["service"]["avg_seconds"] == 300.0  # only C1: 5 min
    assert body["metrics"]["service"]["sample_count"] == 1


def test_store_isolation(client, auth_header, seeded):
    db = seeded["db"]
    store_a = seeded["store"].id
    other = Company(name="Outra AN", external_code="AN11")
    db.add(other)
    db.flush()
    store_b = Store(company_id=other.id, name="Loja B")
    db.add(store_b)
    db.flush()
    dept_b = Department(store_id=store_b.id, code="BB", name="Dept B")
    db.add(dept_b)
    db.flush()
    q_b = Queue(
        department_id=dept_b.id,
        name="Fila B",
        status="OPEN",
        normal_prefix="B",
        priority_prefix="BP",
    )
    db.add(q_b)
    db.flush()
    day = date.today()
    start = datetime.combine(day, datetime.min.time())
    db.add(
        Ticket(
            queue_id=q_b.id,
            sequence_number=1,
            display_number="BX1",
            period_key=day.isoformat(),
            ticket_type=TicketType.NORMAL.value,
            status=TicketStatus.COMPLETED.value,
            issued_at=start + timedelta(hours=1),
            called_at=start + timedelta(hours=1, minutes=1),
            service_started_at=start + timedelta(hours=1, minutes=1),
            completed_at=start + timedelta(hours=1, minutes=2),
        )
    )
    db.commit()

    a = client.get(
        "/api/v1/analytics/overview",
        params={"store_id": store_a, "from": day.isoformat(), "to": day.isoformat()},
        headers=auth_header,
    ).json()
    b = client.get(
        "/api/v1/analytics/overview",
        params={"store_id": store_b.id, "from": day.isoformat(), "to": day.isoformat()},
        headers=auth_header,
    ).json()
    assert b["metrics"]["issued"] >= 1
    # loja A não inclui tickets da B
    assert all(q["name"] != "Fila B" for q in a["queues"])


def test_no_show_not_cancelled(client, auth_header, seeded):
    db = seeded["db"]
    store_id = seeded["store"].id
    qid = seeded["queue"].id
    day = date.today()
    start = datetime.combine(day, datetime.min.time())
    db.add(
        Ticket(
            queue_id=qid,
            sequence_number=4001,
            display_number="UNS1",
            period_key=day.isoformat(),
            ticket_type=TicketType.NORMAL.value,
            status=TicketStatus.NO_SHOW.value,
            issued_at=start + timedelta(hours=1),
            called_at=start + timedelta(hours=1, minutes=3),
            no_show_at=start + timedelta(hours=1, minutes=8),
        )
    )
    db.add(
        Ticket(
            queue_id=qid,
            sequence_number=4002,
            display_number="UCA1",
            period_key=day.isoformat(),
            ticket_type=TicketType.NORMAL.value,
            status=TicketStatus.CANCELLED.value,
            issued_at=start + timedelta(hours=2),
            cancelled_at=start + timedelta(hours=2, minutes=1),
        )
    )
    db.commit()
    body = client.get(
        "/api/v1/analytics/overview",
        params={"store_id": store_id, "from": day.isoformat(), "to": day.isoformat()},
        headers=auth_header,
    ).json()
    assert body["metrics"]["no_show"] == 1
    assert body["metrics"]["cancelled"] == 1


def test_queue_filter_matches_comparison(client, auth_header, seeded):
    store_id = seeded["store"].id
    qid = seeded["queue"].id
    day = date.today().isoformat()
    # ensure some traffic via API
    client.post(
        f"/api/v1/queues/{qid}/tickets",
        json={"type": "NORMAL"},
        headers={**auth_header, "Idempotency-Key": "ux11-f1"},
    )
    all_rows = client.get(
        "/api/v1/analytics/overview",
        params={"store_id": store_id, "from": day, "to": day},
        headers=auth_header,
    ).json()
    filtered = client.get(
        "/api/v1/analytics/overview",
        params={"store_id": store_id, "from": day, "to": day, "queue_id": qid},
        headers=auth_header,
    ).json()
    row = next(q for q in all_rows["queues"] if q["queue_id"] == qid)
    assert filtered["metrics"]["issued"] == row["issued"]


def test_devices_snapshot_label_and_summary_compat(client, auth_header, seeded):
    store_id = seeded["store"].id
    day = date.today().isoformat()
    ov = client.get(
        "/api/v1/analytics/overview",
        params={"store_id": store_id, "from": day, "to": day},
        headers=auth_header,
    ).json()
    assert "Situação atual" in ov["devices_current"]["label"]
    assert "não é" in ov["devices_current"]["note"].lower() or "Não é" in ov["devices_current"]["note"]

    # legacy summary still works for Command Center
    s = client.get(
        "/api/v1/analytics/summary",
        params={"day": day, "store_id": store_id},
        headers=auth_header,
    )
    assert s.status_code == 200
    assert "kpis" in s.json()


def test_empty_period(client, auth_header, seeded):
    r = client.get(
        "/api/v1/analytics/overview",
        params={"store_id": seeded["store"].id, "from": "2099-01-01", "to": "2099-01-02"},
        headers=auth_header,
    )
    assert r.status_code == 200
    assert r.json()["empty"] is True
    assert r.json()["metrics"]["issued"] == 0
    assert r.json()["metrics"]["wait"]["avg_seconds"] is None

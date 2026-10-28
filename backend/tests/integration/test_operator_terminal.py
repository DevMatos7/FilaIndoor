from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.db.session import Base
from app.modules.org.models.entities import Company, Department, Store, User
from app.modules.queue.models import entities as queue_entities  # noqa: F401
from app.modules.queue.models.entities import Terminal, Ticket
from app.modules.queue.services.queue_service import QueueService
from tests.integration.test_concurrency import PG_URL, _pg_available

pytestmark_pg = pytest.mark.skipif(not _pg_available(), reason="PostgreSQL indisponível")


def test_operator_panel_and_actions(client, auth_header, seeded):
    qid = seeded["queue"].id
    db = seeded["db"]
    terminal = Terminal(department_id=seeded["department"].id, name="Balcão 1", code="T1")
    db.add(terminal)
    db.commit()
    db.refresh(terminal)

    client.post(
        f"/api/v1/queues/{qid}/tickets",
        json={"type": "NORMAL"},
        headers={**auth_header, "Idempotency-Key": "op-t1"},
    )

    nxt = client.post(
        f"/api/v1/queues/{qid}/next",
        json={"terminal_id": terminal.id, "auto_complete_current": True, "auto_start": True},
        headers={**auth_header, "Idempotency-Key": "op-next-1"},
    )
    assert nxt.status_code == 200, nxt.text
    assert nxt.json()["status"] == "SERVING"
    ticket_id = nxt.json()["id"]

    panel = client.get(
        f"/api/v1/queues/{qid}/operator-panel",
        params={"terminal_id": terminal.id},
        headers=auth_header,
    )
    assert panel.status_code == 200
    assert panel.json()["serving"]["id"] == ticket_id

    recall = client.post(
        f"/api/v1/tickets/{ticket_id}/recall",
        json={"terminal_id": terminal.id},
        headers=auth_header,
    )
    assert recall.status_code == 200

    done = client.post(
        f"/api/v1/tickets/{ticket_id}/complete",
        json={"terminal_id": terminal.id},
        headers=auth_header,
    )
    assert done.status_code == 200
    assert done.json()["status"] == "COMPLETED"


def test_no_show_flow(client, auth_header, seeded):
    qid = seeded["queue"].id
    db = seeded["db"]
    terminal = Terminal(department_id=seeded["department"].id, name="Balcão 2", code="T2")
    db.add(terminal)
    db.commit()
    db.refresh(terminal)

    client.post(
        f"/api/v1/queues/{qid}/tickets",
        json={"type": "NORMAL"},
        headers={**auth_header, "Idempotency-Key": "op-ns-1"},
    )
    called = client.post(
        f"/api/v1/queues/{qid}/next",
        json={"terminal_id": terminal.id, "auto_start": False},
        headers={**auth_header, "Idempotency-Key": "op-ns-next"},
    ).json()
    noshow = client.post(
        f"/api/v1/tickets/{called['id']}/no-show",
        json={"terminal_id": terminal.id},
        headers=auth_header,
    )
    assert noshow.status_code == 200
    assert noshow.json()["status"] == "NO_SHOW"


@pytestmark_pg
def test_two_terminals_never_call_same_ticket():
    engine = create_engine(PG_URL, pool_size=10, max_overflow=20, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = Session()
    try:
        suffix = __import__("uuid").uuid4().hex[:8]
        company = Company(name=f"OpCo-{suffix}")
        db.add(company)
        db.flush()
        store = Store(company_id=company.id, name="Loja")
        db.add(store)
        db.flush()
        dept = Department(store_id=store.id, code="ACOU", name="Açougue")
        db.add(dept)
        db.flush()
        db.add(User(email=f"op@{suffix}.local", full_name="Op", hashed_password=hash_password("x"), role="operator"))
        db.commit()
        queue = QueueService(db).create_queue(department_id=dept.id, name=f"Fila-{suffix}")
        queue_id = queue.id
        for _ in range(10):
            QueueService(db).create_ticket(queue_id, ticket_type="NORMAL")
        t1 = Terminal(department_id=dept.id, name="B1", code=f"A-{suffix}")
        t2 = Terminal(department_id=dept.id, name="B2", code=f"B-{suffix}")
        db.add_all([t1, t2])
        db.commit()
        db.refresh(t1)
        db.refresh(t2)
        term_ids = [t1.id, t2.id]
    finally:
        db.close()

    def call(i: int):
        s = Session()
        try:
            return QueueService(s).call_next(
                queue_id,
                terminal_id=term_ids[i % 2],
                operator_id=f"op{i}",
                auto_complete_current=False,
                auto_start=False,
            )
        except Exception as exc:  # noqa: BLE001
            return {"error": str(exc)}
        finally:
            s.close()

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(call, range(8)))

    ok = [r for r in results if "id" in r]
    ids = [r["id"] for r in ok]
    assert len(ids) == len(set(ids)), f"Senha duplicada entre terminais: {ids}"
    assert len(ok) >= 2

    db = Session()
    try:
        called = db.scalars(
            select(Ticket).where(Ticket.queue_id == queue_id, Ticket.status.in_(["CALLED", "SERVING"]))
        ).all()
        assert len({t.id for t in called}) == len(called)
    finally:
        db.close()
        engine.dispose()

"""Teste de concorrência na emissão de senhas (PostgreSQL)."""
from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.modules.org.models.entities import Company, Department, Store
from app.modules.queue.models import entities as queue_entities  # noqa: F401
from app.modules.queue.models.entities import Ticket
from app.modules.queue.services.queue_service import QueueService

PG_URL = os.getenv(
    "CONCURRENCY_DATABASE_URL",
    "postgresql+psycopg://fila:fila@localhost:5455/filaindoor",
)


def _pg_available() -> bool:
    try:
        engine = create_engine(PG_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _pg_available(), reason="PostgreSQL não disponível para teste de concorrência")


@pytest.fixture(scope="module")
def pg_engine():
    engine = create_engine(PG_URL, pool_size=20, max_overflow=40, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


def _seed_queue(engine):
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = Session()
    try:
        suffix = uuid.uuid4().hex[:8]
        company = Company(name=f"Co-{suffix}")
        db.add(company)
        db.flush()
        store = Store(company_id=company.id, name=f"Loja-{suffix}")
        db.add(store)
        db.flush()
        dept = Department(store_id=store.id, code="ACOU", name="Açougue")
        db.add(dept)
        db.flush()
        db.commit()
        queue = QueueService(db).create_queue(department_id=dept.id, name=f"Fila-{suffix}")
        return queue.id, Session
    finally:
        db.close()


def test_100_concurrent_ticket_numbers_unique(pg_engine):
    queue_id, Session = _seed_queue(pg_engine)

    def create_one(_: int) -> str:
        s = Session()
        try:
            return QueueService(s).create_ticket(queue_id, ticket_type="NORMAL")["number"]
        finally:
            s.close()

    numbers: list[str] = []
    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = [pool.submit(create_one, i) for i in range(100)]
        for fut in as_completed(futures):
            numbers.append(fut.result())

    assert len(numbers) == 100
    assert len(set(numbers)) == 100

    db = Session()
    try:
        rows = db.scalars(select(Ticket).where(Ticket.queue_id == queue_id)).all()
        assert len(rows) == 100
        assert len({t.display_number for t in rows}) == 100
    finally:
        db.close()


def test_concurrent_next_does_not_double_call(pg_engine):
    queue_id, Session = _seed_queue(pg_engine)
    db = Session()
    try:
        svc = QueueService(db)
        for _ in range(5):
            svc.create_ticket(queue_id, ticket_type="NORMAL")
    finally:
        db.close()

    def call_next(i: int):
        s = Session()
        try:
            return QueueService(s).call_next(
                queue_id,
                terminal_id=f"T{i}",
                operator_id=f"op{i}",
                auto_complete_current=False,
            )
        except Exception as exc:  # noqa: BLE001
            return {"error": str(exc)}
        finally:
            s.close()

    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(call_next, range(5)))

    ok = [r for r in results if "id" in r]
    ids = [r["id"] for r in ok]
    assert len(ids) == len(set(ids)), f"Senha chamada em duplicidade: {ids}"
    assert len(ok) >= 1

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# SQLite em memória para testes de integração sequenciais
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret"

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import Base, get_db
from app.main import app
from app.modules.org.models.entities import Company, Department, Store, User
from app.modules.queue.models import entities as queue_entities  # noqa: F401
from app.modules.signage import models as signage_models  # noqa: F401
from app.modules.devices import models as device_models  # noqa: F401
from app.modules.edge import models as edge_models  # noqa: F401
from app.modules.integration import models as integration_models  # noqa: F401
from app.modules.toledo import models as toledo_models  # noqa: F401
from app.modules.real_plus import models as real_plus_models  # noqa: F401
from app.modules.queue.services.queue_service import QueueService

get_settings.cache_clear()


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def seeded(db_session):
    company = Company(name="Real Teste", external_code="REAL")
    db_session.add(company)
    db_session.flush()
    store = Store(company_id=company.id, name="Loja Teste")
    db_session.add(store)
    db_session.flush()
    dept = Department(store_id=store.id, code="ACOU", name="Açougue")
    db_session.add(dept)
    db_session.flush()
    admin = User(
        email="admin@test.local",
        full_name="Admin",
        hashed_password=hash_password("admin123"),
        role="admin",
        company_id=company.id,
        store_id=store.id,
    )
    db_session.add(admin)
    db_session.commit()

    service = QueueService(db_session)
    queue = service.create_queue(
        department_id=dept.id,
        name="Fila Açougue",
        normal_weight=3,
        priority_weight=1,
        priority_max_wait_seconds=600,
    )
    queue.kiosk_enabled = True
    queue.kiosk_token = "kiosk-test-token"
    queue.department_display_name = "Açougue"
    db_session.add(queue)
    db_session.commit()
    db_session.refresh(queue)
    return {
        "db": db_session,
        "company": company,
        "store": store,
        "department": dept,
        "admin": admin,
        "queue": queue,
        "kiosk_token": queue.kiosk_token,
        "service": QueueService(db_session),
    }


@pytest.fixture()
def client(seeded):
    session = seeded["db"]

    def _override():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_header(client):
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@test.local", "password": "admin123"},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

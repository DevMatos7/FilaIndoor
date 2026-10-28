from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import QUEUE_ADMIN, QUEUE_MANAGER, QUEUE_VIEW
from app.db.session import get_db
from app.modules.auth.deps import require_permissions
from app.modules.org.models.entities import Company, Department, Store, User
from app.modules.org.schemas.org import CompanyCreate, DepartmentCreate, StoreCreate

router = APIRouter(tags=["org"])


@router.get("/companies")
def list_companies(
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    rows = db.scalars(select(Company).order_by(Company.name)).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "external_code": c.external_code,
            "active": c.active,
        }
        for c in rows
    ]


@router.post("/companies", status_code=201)
def create_company(
    body: CompanyCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(QUEUE_ADMIN)),
):
    company = Company(name=body.name, external_code=body.external_code)
    db.add(company)
    db.commit()
    db.refresh(company)
    return {"id": company.id, "name": company.name, "external_code": company.external_code, "active": company.active}


@router.get("/stores")
def list_stores(
    company_id: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    stmt = select(Store).order_by(Store.name)
    if company_id:
        stmt = stmt.where(Store.company_id == company_id)
    rows = db.scalars(stmt).all()
    return [
        {
            "id": s.id,
            "company_id": s.company_id,
            "name": s.name,
            "timezone": s.timezone,
            "external_code": s.external_code,
            "active": s.active,
        }
        for s in rows
    ]


@router.post("/stores", status_code=201)
def create_store(
    body: StoreCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(QUEUE_ADMIN)),
):
    store = Store(
        company_id=body.company_id,
        name=body.name,
        timezone=body.timezone,
        external_code=body.external_code,
    )
    db.add(store)
    db.commit()
    db.refresh(store)
    return {
        "id": store.id,
        "company_id": store.company_id,
        "name": store.name,
        "timezone": store.timezone,
        "active": store.active,
    }


@router.get("/departments")
def list_departments(
    store_id: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    stmt = select(Department).order_by(Department.name)
    if store_id:
        stmt = stmt.where(Department.store_id == store_id)
    rows = db.scalars(stmt).all()
    return [
        {
            "id": d.id,
            "store_id": d.store_id,
            "code": d.code,
            "name": d.name,
            "active": d.active,
        }
        for d in rows
    ]


@router.post("/departments", status_code=201)
def create_department(
    body: DepartmentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(QUEUE_ADMIN)),
):
    dept = Department(store_id=body.store_id, code=body.code, name=body.name)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return {
        "id": dept.id,
        "store_id": dept.store_id,
        "code": dept.code,
        "name": dept.name,
        "active": dept.active,
    }

from pydantic import BaseModel, Field


class CompanyCreate(BaseModel):
    name: str
    external_code: str | None = None


class StoreCreate(BaseModel):
    company_id: str
    name: str
    timezone: str = "America/Sao_Paulo"
    external_code: str | None = None


class DepartmentCreate(BaseModel):
    store_id: str
    code: str = Field(min_length=1, max_length=40)
    name: str

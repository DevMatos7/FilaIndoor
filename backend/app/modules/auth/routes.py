from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError
from app.core.permissions import ROLE_PERMISSIONS
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.modules.auth.deps import get_current_user
from app.modules.org.models.entities import User

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: str
    permissions: list[str]
    company_id: str | None
    store_id: str | None


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == form.username))
    if not user or not verify_password(form.password, user.hashed_password):
        raise UnauthorizedError("Credenciais inválidas")
    token = create_access_token(user.id, extra={"role": user.role})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)):
    return MeResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        permissions=ROLE_PERMISSIONS.get(user.role, []),
        company_id=user.company_id,
        store_id=user.store_id,
    )

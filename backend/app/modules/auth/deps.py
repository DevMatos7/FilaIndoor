from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.permissions import ROLE_PERMISSIONS
from app.core.security import decode_token
from app.db.session import get_db
from app.modules.org.models.entities import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise UnauthorizedError("Token ausente")
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise UnauthorizedError("Token inválido")
    user = db.get(User, payload["sub"])
    if not user or not user.active:
        raise UnauthorizedError("Usuário inválido")
    return user


def require_permissions(*needed: str):
    def _dep(user: User = Depends(get_current_user)) -> User:
        allowed = set(ROLE_PERMISSIONS.get(user.role, []))
        if user.role == "admin":
            return user
        if not needed:
            return user
        if not any(p in allowed for p in needed):
            raise ForbiddenError("Permissão negada")
        return user

    return _dep


def get_idempotency_key(idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")) -> str | None:
    return idempotency_key

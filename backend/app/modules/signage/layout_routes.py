from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.permissions import QUEUE_ADMIN, QUEUE_MANAGER, SIGNAGE_ADMIN, SIGNAGE_EDITOR, SIGNAGE_VIEWER
from app.db.session import get_db
from app.modules.auth.deps import require_permissions
from app.modules.org.models.entities import User
from app.modules.signage.layout_service import LayoutService

router = APIRouter(tags=["layouts"])


@router.get("/layout-templates")
def list_layout_templates(
    store_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(
        require_permissions(SIGNAGE_VIEWER, SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)
    ),
):
    """Read-only listing of system (+ optional store) layout templates."""
    return LayoutService(db).list_templates(store_id=store_id)


@router.get("/layout-templates/{template_id}")
def get_layout_template(
    template_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(
        require_permissions(SIGNAGE_VIEWER, SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)
    ),
):
    return LayoutService(db).get_template(template_id)

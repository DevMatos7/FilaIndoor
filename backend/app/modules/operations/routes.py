from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.permissions import ANALYTICS_VIEW, DEVICE_VIEW, QUEUE_ADMIN, QUEUE_MANAGER, QUEUE_VIEW
from app.db.session import get_db
from app.modules.auth.deps import require_permissions
from app.modules.operations.service import OperationsService
from app.modules.org.models.entities import User

router = APIRouter(prefix="/operations", tags=["operations"])


@router.get("/overview")
def operations_overview(
    store_id: str = Query(..., description="Loja selecionada no StoreContext"),
    db: Session = Depends(get_db),
    _: User = Depends(
        require_permissions(ANALYTICS_VIEW, QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN, DEVICE_VIEW)
    ),
):
    """Command Center — agregação read-only por loja (sem migration / sem side-effects)."""
    return OperationsService(db).overview(store_id)

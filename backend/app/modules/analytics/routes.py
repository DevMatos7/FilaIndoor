from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.core.permissions import ANALYTICS_VIEW, QUEUE_ADMIN, QUEUE_MANAGER, QUEUE_VIEW
from app.db.session import get_db
from app.modules.analytics.service import AnalyticsService
from app.modules.auth.deps import require_permissions
from app.modules.org.models.entities import User

router = APIRouter(tags=["analytics"])


@router.get("/analytics/summary")
def analytics_summary(
    day: date | None = Query(default=None, description="YYYY-MM-DD (UTC)"),
    queue_id: str | None = Query(default=None),
    store_id: str | None = Query(default=None, description="Filtra filas da loja (ignorado se queue_id)"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(ANALYTICS_VIEW, QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return AnalyticsService(db).summary(day=day, queue_id=queue_id, store_id=store_id)


@router.get("/analytics/overview")
def analytics_overview(
    store_id: str = Query(..., description="Loja obrigatória"),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    queue_id: str | None = Query(default=None),
    ticket_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(ANALYTICS_VIEW, QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    today = date.today()
    d_from = date_from or today
    d_to = date_to or d_from
    if d_to < d_from:
        raise ValidationError("Data final deve ser posterior ou igual à data inicial")
    if (d_to - d_from).days > 366:
        raise ValidationError("Período máximo de 366 dias")
    if ticket_type and ticket_type.upper() not in {"NORMAL", "PRIORITY", "PRIORITY_PLUS", "CUSTOM"}:
        raise ValidationError("ticket_type inválido")
    return AnalyticsService(db).overview(
        store_id=store_id,
        date_from=d_from,
        date_to=d_to,
        queue_id=queue_id,
        ticket_type=ticket_type.upper() if ticket_type else None,
    )

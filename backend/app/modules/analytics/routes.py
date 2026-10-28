from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

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
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(ANALYTICS_VIEW, QUEUE_VIEW, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return AnalyticsService(db).summary(day=day, queue_id=queue_id)

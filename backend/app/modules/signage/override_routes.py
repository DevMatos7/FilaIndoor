from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.permissions import QUEUE_ADMIN, QUEUE_MANAGER, SIGNAGE_ADMIN, SIGNAGE_EDITOR, SIGNAGE_VIEWER
from app.db.session import get_db
from app.modules.auth.deps import require_permissions
from app.modules.org.models.entities import User
from app.modules.signage.override_service import ScreenOverrideService

router = APIRouter(tags=["screen-overrides"])


class OverrideCreate(BaseModel):
    store_id: str
    override_type: str
    target_scope: str = "STORE"
    target_id: str | None = None
    payload: dict = Field(default_factory=dict)
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    duration_seconds: int | None = Field(default=None, ge=1, le=86400)
    dedupe_key: str | None = None
    source_type: str | None = "MANUAL_API"
    source_id: str | None = None


@router.get("/screen-overrides")
def list_screen_overrides(
    store_id: str = Query(...),
    active: bool | None = Query(default=None),
    override_type: str | None = Query(default=None),
    target_scope: str | None = Query(default=None),
    target_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(
        require_permissions(SIGNAGE_VIEWER, SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)
    ),
):
    return ScreenOverrideService(db).list_overrides(
        store_id=store_id,
        active=active,
        override_type=override_type,
        target_scope=target_scope,
        target_id=target_id,
    )


@router.post("/screen-overrides", status_code=201)
def create_screen_override(
    body: OverrideCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_permissions(SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)
    ),
):
    return ScreenOverrideService(db).create(
        store_id=body.store_id,
        override_type=body.override_type,
        target_scope=body.target_scope,
        target_id=body.target_id,
        payload=body.payload,
        starts_at=body.starts_at,
        expires_at=body.expires_at,
        duration_seconds=body.duration_seconds,
        dedupe_key=body.dedupe_key,
        source_type=body.source_type,
        source_id=body.source_id,
        created_by_user_id=user.id,
        allow_queue_call=False,
        publish_ws=True,
    )


@router.post("/screen-overrides/{override_id}/cancel")
def cancel_screen_override(
    override_id: str,
    store_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(
        require_permissions(SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)
    ),
):
    return ScreenOverrideService(db).cancel(override_id, store_id=store_id)

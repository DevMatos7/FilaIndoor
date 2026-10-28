from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.permissions import QUEUE_ADMIN, QUEUE_MANAGER, SIGNAGE_ADMIN, SIGNAGE_EDITOR, SIGNAGE_VIEWER
from app.db.session import get_db
from app.modules.auth.deps import require_permissions
from app.modules.org.models.entities import User
from app.modules.signage.schedule_service import ScheduleService

router = APIRouter(tags=["channels"])


class ChannelCreate(BaseModel):
    store_id: str
    name: str = Field(min_length=1, max_length=180)
    layout: str = "queue_media_split"
    default_playlist_id: str | None = None


class ChannelUpdate(BaseModel):
    name: str | None = None
    layout: str | None = None
    default_playlist_id: str | None = None
    active: bool | None = None


class GroupCreate(BaseModel):
    store_id: str
    channel_id: str
    name: str = Field(min_length=1, max_length=180)


class ScheduleCreate(BaseModel):
    channel_id: str
    playlist_id: str
    name: str = "Agenda"
    start_date: str | None = None
    end_date: str | None = None
    start_time: str = "00:00"
    end_time: str = "23:59"
    days_of_week: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6])
    priority: str = "NORMAL"


class ScheduleUpdate(BaseModel):
    name: str | None = None
    playlist_id: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    days_of_week: list[int] | None = None
    priority: str | None = None
    active: bool | None = None


@router.get("/channels")
def list_channels(
    store_id: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(SIGNAGE_VIEWER, SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return ScheduleService(db).list_channels(store_id=store_id)


@router.post("/channels", status_code=201)
def create_channel(
    body: ChannelCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return ScheduleService(db).create_channel(**body.model_dump())


@router.get("/channels/{channel_id}")
def get_channel(
    channel_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(SIGNAGE_VIEWER, SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return ScheduleService(db).get_channel(channel_id)


@router.patch("/channels/{channel_id}")
def patch_channel(
    channel_id: str,
    body: ChannelUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return ScheduleService(db).update_channel(channel_id, **body.model_dump(exclude_unset=True))


@router.post("/screen-groups", status_code=201)
def create_group(
    body: GroupCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return ScheduleService(db).create_group(**body.model_dump())


@router.post("/schedules", status_code=201)
def create_schedule(
    body: ScheduleCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    data = body.model_dump()
    channel_id = data.pop("channel_id")
    playlist_id = data.pop("playlist_id")
    return ScheduleService(db).create_schedule(channel_id=channel_id, playlist_id=playlist_id, **data)


@router.patch("/schedules/{schedule_id}")
def patch_schedule(
    schedule_id: str,
    body: ScheduleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return ScheduleService(db).update_schedule(schedule_id, **body.model_dump(exclude_unset=True))


@router.delete("/schedules/{schedule_id}")
def delete_schedule(
    schedule_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return ScheduleService(db).delete_schedule(schedule_id)


@router.get("/channels/{channel_id}/now")
def channel_now(
    channel_id: str,
    at: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(SIGNAGE_VIEWER, SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return ScheduleService(db).active_at(channel_id, at)


@router.get("/channels/{channel_id}/conflicts")
def channel_conflicts(
    channel_id: str,
    at: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(SIGNAGE_VIEWER, SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return ScheduleService(db).list_conflicts(channel_id, at)

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.permissions import QUEUE_ADMIN, QUEUE_MANAGER, SIGNAGE_ADMIN, SIGNAGE_EDITOR, SIGNAGE_VIEWER
from app.db.session import get_db
from app.modules.auth.deps import require_permissions
from app.modules.org.models.entities import User
from app.modules.signage.service import SignageService

router = APIRouter(tags=["media"])


class WebMediaRequest(BaseModel):
    store_id: str
    name: str = Field(min_length=1, max_length=180)
    url: str
    duration_seconds: int | None = 15
    notes: str | None = None


class MediaUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    notes: str | None = None
    duration_seconds: int | None = Field(default=None, ge=1, le=86400)
    store_id: str | None = None


@router.get("/media/limits")
def media_limits(
    _: User = Depends(require_permissions(SIGNAGE_VIEWER, SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    """Limites conhecidos do upload — aditivo UX-7."""
    s = get_settings()
    return {
        "image_max_mb": s.media_max_image_mb,
        "video_max_mb": s.media_max_video_mb,
        "image_mimes": ["image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml"],
        "video_mimes": ["video/mp4", "video/webm"],
    }


@router.get("/media")
def list_media(
    store_id: str | None = None,
    media_type: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(SIGNAGE_VIEWER, SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return SignageService(db).list_assets(store_id=store_id, media_type=media_type)


@router.get("/media/{asset_id}")
def get_media(
    asset_id: str,
    store_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(SIGNAGE_VIEWER, SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return SignageService(db).get_dict(asset_id, store_id=store_id)


@router.post("/media", status_code=201)
async def upload_media(
    store_id: str = Form(...),
    name: str = Form(...),
    duration_seconds: int | None = Form(default=None),
    notes: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions(SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    content = await file.read()
    return SignageService(db).create_upload(
        store_id=store_id,
        name=name,
        filename=file.filename or "upload.bin",
        content_type=file.content_type,
        content=content,
        duration_seconds=duration_seconds,
        notes=notes,
        created_by=user.id,
    )


@router.post("/media/web", status_code=201)
def create_web_media(
    body: WebMediaRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions(SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return SignageService(db).create_web(
        store_id=body.store_id,
        name=body.name,
        url=body.url,
        duration_seconds=body.duration_seconds,
        notes=body.notes,
        created_by=user.id,
    )


@router.patch("/media/{asset_id}")
def update_media(
    asset_id: str,
    body: MediaUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return SignageService(db).update(
        asset_id,
        store_id=body.store_id,
        name=body.name,
        notes=body.notes,
        duration_seconds=body.duration_seconds,
    )


@router.delete("/media/{asset_id}")
def delete_media(
    asset_id: str,
    hard: bool = False,
    store_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    service = SignageService(db)
    if hard:
        return service.hard_delete(asset_id, store_id=store_id)
    return service.soft_delete(asset_id, store_id=store_id)

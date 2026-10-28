from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.permissions import QUEUE_ADMIN, QUEUE_MANAGER, SIGNAGE_ADMIN, SIGNAGE_EDITOR, SIGNAGE_VIEWER
from app.db.session import get_db
from app.modules.auth.deps import require_permissions
from app.modules.org.models.entities import User
from app.modules.signage.service import SignageService, asset_to_dict

router = APIRouter(tags=["media"])


class WebMediaRequest(BaseModel):
    store_id: str
    name: str = Field(min_length=1, max_length=180)
    url: str
    duration_seconds: int | None = 15
    notes: str | None = None


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
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(SIGNAGE_VIEWER, SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return asset_to_dict(SignageService(db).get(asset_id))


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


@router.delete("/media/{asset_id}")
def delete_media(
    asset_id: str,
    hard: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    service = SignageService(db)
    if hard:
        return service.hard_delete(asset_id)
    return service.soft_delete(asset_id)

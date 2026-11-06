from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.core.permissions import QUEUE_ADMIN, QUEUE_MANAGER, SIGNAGE_ADMIN, SIGNAGE_EDITOR, SIGNAGE_VIEWER
from app.db.session import get_db
from app.modules.auth.deps import require_permissions
from app.modules.org.models.entities import User
from app.modules.signage.playlist_service import PlaylistService

router = APIRouter(tags=["playlists"])


class PlaylistCreate(BaseModel):
    store_id: str
    name: str = Field(min_length=1, max_length=180)
    description: str | None = None
    is_default: bool = False


class PlaylistUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    active: bool | None = None
    is_default: bool | None = None
    store_id: str | None = None


class PlaylistItemCreate(BaseModel):
    item_type: str | None = None  # MEDIA | DYNAMIC — default inferred
    asset_id: str | None = None
    dynamic_content_id: str | None = None
    duration_seconds: int | None = Field(default=None, ge=1, le=86400)
    duration_source: str | None = None
    position: int | None = None

    @model_validator(mode="after")
    def validate_xor(self):
        itype = (self.item_type or ("DYNAMIC" if self.dynamic_content_id else "MEDIA")).upper()
        if itype == "MEDIA":
            if not self.asset_id:
                raise ValueError("asset_id obrigatório para MEDIA")
            if self.dynamic_content_id:
                raise ValueError("dynamic_content_id não permitido para MEDIA")
        elif itype == "DYNAMIC":
            if not self.dynamic_content_id:
                raise ValueError("dynamic_content_id obrigatório para DYNAMIC")
            if self.asset_id:
                raise ValueError("asset_id não permitido para DYNAMIC")
        else:
            raise ValueError("item_type inválido")
        self.item_type = itype
        return self


class PlaylistItemsBulkCreate(BaseModel):
    asset_ids: list[str] | None = None
    items: list[dict[str, Any]] | None = None
    store_id: str | None = None

    @model_validator(mode="after")
    def require_one(self):
        if not self.asset_ids and not self.items:
            raise ValueError("Informe asset_ids ou items")
        return self


class PlaylistItemUpdate(BaseModel):
    duration_seconds: int | None = Field(default=None, ge=1, le=86400)
    duration_source: str | None = None
    active: bool | None = None
    store_id: str | None = None


class ReorderRequest(BaseModel):
    item_ids: list[str]
    store_id: str | None = None


@router.get("/playlists")
def list_playlists(
    store_id: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(SIGNAGE_VIEWER, SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return PlaylistService(db).list_playlists(store_id=store_id)


@router.post("/playlists", status_code=201)
def create_playlist(
    body: PlaylistCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return PlaylistService(db).create(**body.model_dump())


@router.get("/playlists/{playlist_id}")
def get_playlist(
    playlist_id: str,
    store_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(SIGNAGE_VIEWER, SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return PlaylistService(db).get(playlist_id, store_id=store_id)


@router.patch("/playlists/{playlist_id}")
def patch_playlist(
    playlist_id: str,
    body: PlaylistUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    data = body.model_dump(exclude_unset=True)
    store_id = data.pop("store_id", None)
    return PlaylistService(db).update(playlist_id, store_id=store_id, **data)


@router.delete("/playlists/{playlist_id}")
def delete_playlist(
    playlist_id: str,
    store_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return PlaylistService(db).delete(playlist_id, store_id=store_id)


@router.post("/playlists/{playlist_id}/items", status_code=201)
def add_item(
    playlist_id: str,
    body: PlaylistItemCreate,
    store_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return PlaylistService(db).add_item(playlist_id, store_id=store_id, **body.model_dump())


@router.post("/playlists/{playlist_id}/items/bulk", status_code=201)
def add_items_bulk(
    playlist_id: str,
    body: PlaylistItemsBulkCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return PlaylistService(db).add_items(
        playlist_id,
        asset_ids=body.asset_ids,
        items=body.items,
        store_id=body.store_id,
    )


@router.patch("/playlists/{playlist_id}/items/reorder")
def reorder_items(
    playlist_id: str,
    body: ReorderRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return PlaylistService(db).reorder(
        playlist_id, body.item_ids, store_id=body.store_id
    )


@router.patch("/playlists/{playlist_id}/items/{item_id}")
def patch_item(
    playlist_id: str,
    item_id: str,
    body: PlaylistItemUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    data = body.model_dump(exclude_unset=True)
    store_id = data.pop("store_id", None)
    return PlaylistService(db).update_item(playlist_id, item_id, store_id=store_id, **data)


@router.delete("/playlists/{playlist_id}/items/{item_id}")
def remove_item(
    playlist_id: str,
    item_id: str,
    store_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(SIGNAGE_EDITOR, SIGNAGE_ADMIN, QUEUE_MANAGER, QUEUE_ADMIN)),
):
    return PlaylistService(db).remove_item(playlist_id, item_id, store_id=store_id)

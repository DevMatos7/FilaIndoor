from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.permissions import RETAIL_CONTENT_ADMIN, RETAIL_CONTENT_EDITOR, RETAIL_CONTENT_VIEWER
from app.db.session import get_db
from app.modules.auth.deps import require_permissions
from app.modules.dynamic_content.content_service import DynamicContentService
from app.modules.org.models.entities import User

router = APIRouter(tags=["dynamic-content"])


class ContentBody(BaseModel):
    name: str
    description: str | None = None
    selection_mode: str
    template_id: str
    config: dict[str, Any] = Field(default_factory=dict)
    rule: dict[str, Any] | None = None
    products: list[dict[str, Any]] = Field(default_factory=list)


class ContentPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    selection_mode: str | None = None
    template_id: str | None = None
    config: dict[str, Any] | None = None
    rule: dict[str, Any] | None = None
    products: list[dict[str, Any]] | None = None


@router.get("/dynamic-content/overview")
def overview(
    store_id: str = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(RETAIL_CONTENT_VIEWER, RETAIL_CONTENT_ADMIN)),
):
    return DynamicContentService(db).overview(store_id)


@router.get("/dynamic-content/templates")
def list_templates(
    store_id: str | None = None,
    content_type: str | None = "PRICE_TABLE",
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(RETAIL_CONTENT_VIEWER, RETAIL_CONTENT_ADMIN)),
):
    return DynamicContentService(db).list_templates(store_id=store_id, content_type=content_type)


@router.get("/dynamic-content/templates/{template_id}")
def get_template(
    template_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(RETAIL_CONTENT_VIEWER, RETAIL_CONTENT_ADMIN)),
):
    return DynamicContentService(db).get_template(template_id)


@router.get("/dynamic-content")
def list_contents(
    store_id: str = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(RETAIL_CONTENT_VIEWER, RETAIL_CONTENT_ADMIN)),
):
    return DynamicContentService(db).list_contents(store_id)


@router.post("/dynamic-content")
def create_content(
    body: ContentBody,
    store_id: str = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions(RETAIL_CONTENT_EDITOR, RETAIL_CONTENT_ADMIN)),
):
    return DynamicContentService(db).create_content(store_id, body.model_dump(), user_id=user.id)


@router.get("/dynamic-content/{content_id}")
def get_content(
    content_id: str,
    store_id: str = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(RETAIL_CONTENT_VIEWER, RETAIL_CONTENT_ADMIN)),
):
    return DynamicContentService(db).get_content(content_id, store_id)


@router.patch("/dynamic-content/{content_id}")
def patch_content(
    content_id: str,
    body: ContentPatch,
    store_id: str = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(RETAIL_CONTENT_EDITOR, RETAIL_CONTENT_ADMIN)),
):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    return DynamicContentService(db).update_content(content_id, store_id, data)


@router.delete("/dynamic-content/{content_id}")
def delete_content(
    content_id: str,
    store_id: str = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(RETAIL_CONTENT_EDITOR, RETAIL_CONTENT_ADMIN)),
):
    return DynamicContentService(db).soft_delete(content_id, store_id)


@router.post("/dynamic-content/{content_id}/resolve")
def resolve_content(
    content_id: str,
    store_id: str = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(RETAIL_CONTENT_EDITOR, RETAIL_CONTENT_ADMIN)),
):
    return DynamicContentService(db).resolve(content_id, store_id)


@router.post("/dynamic-content/{content_id}/invalidate")
def invalidate_content(
    content_id: str,
    store_id: str = Query(...),
    reason: str = Query("MANUAL"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(RETAIL_CONTENT_ADMIN, RETAIL_CONTENT_EDITOR)),
):
    from app.modules.dynamic_content.invalidation_service import DynamicInvalidationService

    return DynamicInvalidationService(db).invalidate_content(content_id, store_id=store_id, reason=reason)


@router.post("/dynamic-content/{content_id}/preview")
def preview_content(
    content_id: str,
    store_id: str = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(RETAIL_CONTENT_VIEWER, RETAIL_CONTENT_ADMIN)),
):
    return DynamicContentService(db).preview(content_id, store_id)


@router.post("/dynamic-content/preview")
def preview_draft(
    body: ContentBody,
    store_id: str = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(RETAIL_CONTENT_EDITOR, RETAIL_CONTENT_ADMIN)),
):
    return DynamicContentService(db).preview_draft(store_id, body.model_dump())

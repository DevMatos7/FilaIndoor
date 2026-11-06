from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.modules.signage.models import MediaAsset, PlaylistItem
from app.modules.signage.storage import checksum, delete_key, save_bytes

IMAGE_MIME = {
    "image/jpeg": "IMAGE",
    "image/jpg": "IMAGE",
    "image/png": "IMAGE",
    "image/webp": "IMAGE",
    "image/gif": "IMAGE",
    "image/svg+xml": "IMAGE",
}
VIDEO_MIME = {
    "video/mp4": "VIDEO",
    "video/webm": "VIDEO",
}


def asset_to_dict(a: MediaAsset, *, usage_count: int | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": a.id,
        "store_id": a.store_id,
        "name": a.name,
        "media_type": a.media_type,
        "mime_type": a.mime_type,
        "original_filename": a.original_filename,
        "public_url": a.public_url,
        "size_bytes": a.size_bytes,
        "duration_seconds": a.duration_seconds,
        "width": a.width,
        "height": a.height,
        "checksum": a.checksum,
        "notes": a.notes,
        "active": a.active,
        "created_by": a.created_by,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }
    if usage_count is not None:
        data["usage_count"] = usage_count
    return data


class SignageService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def _usage_counts(self, asset_ids: list[str]) -> dict[str, int]:
        if not asset_ids:
            return {}
        rows = self.db.execute(
            select(PlaylistItem.asset_id, func.count())
            .where(PlaylistItem.asset_id.in_(asset_ids), PlaylistItem.active.is_(True))
            .group_by(PlaylistItem.asset_id)
        ).all()
        counts = {str(aid): int(cnt) for aid, cnt in rows}
        # DRC-4: ProductMediaLink also counts as usage
        from app.modules.retail.product_media_service import ProductMediaService

        for aid, cnt in ProductMediaService(self.db).count_usage_for_assets(asset_ids).items():
            counts[aid] = counts.get(aid, 0) + cnt
        return counts

    def _assert_store(self, asset: MediaAsset, store_id: str | None) -> None:
        if store_id and asset.store_id != store_id:
            raise ForbiddenError("Conteúdo não pertence à loja")

    def list_assets(
        self,
        *,
        store_id: str | None = None,
        media_type: str | None = None,
        active_only: bool = True,
        include_usage: bool = True,
    ) -> list[dict[str, Any]]:
        stmt = select(MediaAsset).order_by(MediaAsset.created_at.desc())
        if store_id:
            stmt = stmt.where(MediaAsset.store_id == store_id)
        if media_type:
            stmt = stmt.where(MediaAsset.media_type == media_type.upper())
        if active_only:
            stmt = stmt.where(MediaAsset.active.is_(True))
        assets = list(self.db.scalars(stmt).all())
        counts = self._usage_counts([a.id for a in assets]) if include_usage else {}
        return [
            asset_to_dict(a, usage_count=counts.get(a.id, 0) if include_usage else None)
            for a in assets
        ]

    def get(self, asset_id: str, *, store_id: str | None = None) -> MediaAsset:
        asset = self.db.get(MediaAsset, asset_id)
        if not asset or not asset.active:
            raise NotFoundError("Mídia não encontrada")
        self._assert_store(asset, store_id)
        return asset

    def get_dict(self, asset_id: str, *, store_id: str | None = None) -> dict[str, Any]:
        asset = self.get(asset_id, store_id=store_id)
        count = self._usage_counts([asset.id]).get(asset.id, 0)
        return asset_to_dict(asset, usage_count=count)

    def create_web(
        self,
        *,
        store_id: str,
        name: str,
        url: str,
        duration_seconds: int | None = 15,
        notes: str | None = None,
        created_by: str | None = None,
    ) -> dict[str, Any]:
        url = (url or "").strip()
        if not url.startswith(("http://", "https://")):
            raise ValidationError("URL WEB deve começar com http:// ou https://")
        return self._persist(
            MediaAsset(
                store_id=store_id,
                name=name.strip(),
                media_type="WEB",
                mime_type="text/uri-list",
                public_url=url,
                duration_seconds=duration_seconds or 15,
                notes=notes,
                created_by=created_by,
            )
        )

    def create_upload(
        self,
        *,
        store_id: str,
        name: str,
        filename: str,
        content_type: str | None,
        content: bytes,
        duration_seconds: int | None = None,
        notes: str | None = None,
        created_by: str | None = None,
    ) -> dict[str, Any]:
        mime = (content_type or "").split(";")[0].strip().lower() or "application/octet-stream"
        media_type = IMAGE_MIME.get(mime) or VIDEO_MIME.get(mime)
        if not media_type:
            raise ValidationError(f"Tipo de arquivo não suportado: {mime}")

        max_mb = self.settings.media_max_image_mb if media_type == "IMAGE" else self.settings.media_max_video_mb
        if len(content) > max_mb * 1024 * 1024:
            raise ValidationError(f"Arquivo excede o limite de {max_mb} MB")

        if not content:
            raise ValidationError("Arquivo vazio")

        key, _, public = save_bytes(store_id, filename, content)
        default_duration = 10 if media_type == "IMAGE" else (duration_seconds or 15)
        asset = MediaAsset(
            store_id=store_id,
            name=name.strip() or filename,
            media_type=media_type,
            mime_type=mime,
            original_filename=filename,
            storage_key=key,
            public_url=public,
            size_bytes=len(content),
            duration_seconds=duration_seconds or default_duration,
            checksum=checksum(content),
            notes=notes,
            created_by=created_by,
        )
        try:
            return self._persist(asset)
        except Exception:
            delete_key(key)
            raise

    def update(
        self,
        asset_id: str,
        *,
        store_id: str | None = None,
        name: str | None = None,
        notes: str | None = None,
        duration_seconds: int | None = None,
    ) -> dict[str, Any]:
        asset = self.get(asset_id, store_id=store_id)
        if name is not None:
            clean = name.strip()
            if not clean:
                raise ValidationError("Nome obrigatório")
            conflict = self.db.scalar(
                select(MediaAsset).where(
                    MediaAsset.store_id == asset.store_id,
                    MediaAsset.name == clean,
                    MediaAsset.active.is_(True),
                    MediaAsset.id != asset.id,
                )
            )
            if conflict:
                raise ConflictError("Já existe conteúdo ativo com este nome na loja")
            asset.name = clean
        if notes is not None:
            asset.notes = notes
        if duration_seconds is not None:
            if duration_seconds < 1:
                raise ValidationError("Duração inválida")
            asset.duration_seconds = duration_seconds
        self.db.commit()
        self.db.refresh(asset)
        count = self._usage_counts([asset.id]).get(asset.id, 0)
        return asset_to_dict(asset, usage_count=count)

    def soft_delete(self, asset_id: str, *, store_id: str | None = None) -> dict[str, Any]:
        asset = self.get(asset_id, store_id=store_id)
        used = self._usage_counts([asset.id]).get(asset.id, 0)
        if used > 0:
            raise ConflictError(
                "Este conteúdo está em uso (playlist e/ou imagem de produto). "
                "Remova as associações antes de excluir."
            )
        asset.active = False
        self.db.commit()
        return {"id": asset.id, "active": False}

    def hard_delete(self, asset_id: str, *, store_id: str | None = None) -> dict[str, Any]:
        asset = self.db.get(MediaAsset, asset_id)
        if not asset:
            raise NotFoundError("Mídia não encontrada")
        self._assert_store(asset, store_id)
        used = self._usage_counts([asset.id]).get(asset.id, 0)
        if used > 0:
            raise ConflictError(
                "Este conteúdo está em uso (playlist e/ou imagem de produto). "
                "Remova as associações antes de excluir."
            )
        key = asset.storage_key
        self.db.delete(asset)
        self.db.commit()
        delete_key(key)
        return {"id": asset_id, "deleted": True}

    def _persist(self, asset: MediaAsset) -> dict[str, Any]:
        existing = self.db.scalar(
            select(MediaAsset).where(
                MediaAsset.store_id == asset.store_id,
                MediaAsset.name == asset.name,
                MediaAsset.active.is_(True),
            )
        )
        if existing:
            raise ConflictError("Já existe mídia ativa com este nome na loja")
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)
        return asset_to_dict(asset, usage_count=0)

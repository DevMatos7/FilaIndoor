from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.signage.models import MediaAsset, Playlist, PlaylistItem
from app.modules.signage.service import asset_to_dict


def item_to_dict(item: PlaylistItem) -> dict[str, Any]:
    asset = item.asset
    return {
        "id": item.id,
        "playlist_id": item.playlist_id,
        "asset_id": item.asset_id,
        "position": item.position,
        "duration_seconds": item.duration_seconds,
        "active": item.active,
        "asset": asset_to_dict(asset) if asset else None,
    }


def playlist_to_dict(pl: Playlist, *, include_items: bool = True) -> dict[str, Any]:
    items = []
    if include_items:
        active_items = sorted(
            [i for i in (pl.items or []) if i.active],
            key=lambda x: x.position,
        )
        items = [item_to_dict(i) for i in active_items]
    return {
        "id": pl.id,
        "store_id": pl.store_id,
        "name": pl.name,
        "description": pl.description,
        "active": pl.active,
        "is_default": pl.is_default,
        "created_at": pl.created_at.isoformat() if pl.created_at else None,
        "updated_at": pl.updated_at.isoformat() if pl.updated_at else None,
        "items": items,
        "item_count": len(items) if include_items else None,
    }


class PlaylistService:
    def __init__(self, db: Session):
        self.db = db

    def _load(self, playlist_id: str) -> Playlist:
        pl = self.db.scalar(
            select(Playlist)
            .options(joinedload(Playlist.items).joinedload(PlaylistItem.asset))
            .where(Playlist.id == playlist_id)
        )
        if not pl:
            raise NotFoundError("Playlist não encontrada")
        return pl

    def list_playlists(self, store_id: str | None = None, active_only: bool = True) -> list[dict[str, Any]]:
        stmt = select(Playlist).options(joinedload(Playlist.items)).order_by(Playlist.name)
        if store_id:
            stmt = stmt.where(Playlist.store_id == store_id)
        if active_only:
            stmt = stmt.where(Playlist.active.is_(True))
        rows = self.db.scalars(stmt).unique().all()
        return [playlist_to_dict(p) for p in rows]

    def get(self, playlist_id: str) -> dict[str, Any]:
        return playlist_to_dict(self._load(playlist_id))

    def create(
        self,
        *,
        store_id: str,
        name: str,
        description: str | None = None,
        is_default: bool = False,
    ) -> dict[str, Any]:
        name = name.strip()
        if not name:
            raise ValidationError("Nome obrigatório")
        if is_default:
            self._clear_default(store_id)
        pl = Playlist(
            store_id=store_id,
            name=name,
            description=description,
            is_default=is_default,
        )
        self.db.add(pl)
        self.db.commit()
        return playlist_to_dict(self._load(pl.id))

    def update(
        self,
        playlist_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        active: bool | None = None,
        is_default: bool | None = None,
    ) -> dict[str, Any]:
        pl = self._load(playlist_id)
        if name is not None:
            pl.name = name.strip() or pl.name
        if description is not None:
            pl.description = description
        if active is not None:
            pl.active = active
        if is_default is True:
            self._clear_default(pl.store_id)
            pl.is_default = True
        elif is_default is False:
            pl.is_default = False
        self.db.commit()
        return playlist_to_dict(self._load(playlist_id))

    def delete(self, playlist_id: str) -> dict[str, Any]:
        pl = self._load(playlist_id)
        pl.active = False
        self.db.commit()
        return {"id": playlist_id, "active": False}

    def add_item(
        self,
        playlist_id: str,
        *,
        asset_id: str,
        duration_seconds: int | None = None,
        position: int | None = None,
    ) -> dict[str, Any]:
        pl = self._load(playlist_id)
        asset = self.db.get(MediaAsset, asset_id)
        if not asset or not asset.active:
            raise NotFoundError("Mídia não encontrada")
        if asset.store_id != pl.store_id:
            raise ValidationError("Mídia pertence a outra loja")

        active = [i for i in pl.items if i.active]
        if position is None:
            position = (max((i.position for i in active), default=-1) + 1)
        else:
            for i in active:
                if i.position >= position:
                    i.position += 1

        duration = duration_seconds if duration_seconds is not None else (asset.duration_seconds or 10)
        item = PlaylistItem(
            playlist_id=pl.id,
            asset_id=asset.id,
            position=position,
            duration_seconds=max(1, int(duration)),
        )
        self.db.add(item)
        self.db.commit()
        return playlist_to_dict(self._load(playlist_id))

    def update_item(
        self,
        playlist_id: str,
        item_id: str,
        *,
        duration_seconds: int | None = None,
        active: bool | None = None,
    ) -> dict[str, Any]:
        pl = self._load(playlist_id)
        item = next((i for i in pl.items if i.id == item_id), None)
        if not item:
            raise NotFoundError("Item da playlist não encontrado")
        if duration_seconds is not None:
            item.duration_seconds = max(1, int(duration_seconds))
        if active is not None:
            item.active = active
        self.db.commit()
        return playlist_to_dict(self._load(playlist_id))

    def remove_item(self, playlist_id: str, item_id: str) -> dict[str, Any]:
        pl = self._load(playlist_id)
        item = next((i for i in pl.items if i.id == item_id), None)
        if not item:
            raise NotFoundError("Item da playlist não encontrado")
        item.active = False
        # recompacta posições
        active = sorted([i for i in pl.items if i.active and i.id != item_id], key=lambda x: x.position)
        for idx, i in enumerate(active):
            i.position = idx
        self.db.commit()
        return playlist_to_dict(self._load(playlist_id))

    def reorder(self, playlist_id: str, item_ids: list[str]) -> dict[str, Any]:
        pl = self._load(playlist_id)
        active = {i.id: i for i in pl.items if i.active}
        if set(item_ids) != set(active.keys()):
            raise ValidationError("Lista de itens incompleta ou inválida para reordenação")
        for idx, item_id in enumerate(item_ids):
            active[item_id].position = idx
        self.db.commit()
        return playlist_to_dict(self._load(playlist_id))

    def resolve_for_store(self, store_id: str, playlist_id: str | None = None) -> list[dict[str, Any]]:
        """Itens prontos para o player TV."""
        pl: Playlist | None = None
        if playlist_id:
            pl = self.db.scalar(
                select(Playlist)
                .options(joinedload(Playlist.items).joinedload(PlaylistItem.asset))
                .where(Playlist.id == playlist_id, Playlist.active.is_(True))
            )
        if not pl:
            pl = self.db.scalar(
                select(Playlist)
                .options(joinedload(Playlist.items).joinedload(PlaylistItem.asset))
                .where(
                    Playlist.store_id == store_id,
                    Playlist.active.is_(True),
                    Playlist.is_default.is_(True),
                )
            )
        if not pl:
            return []
        items = sorted([i for i in pl.items if i.active and i.asset and i.asset.active], key=lambda x: x.position)
        return [
            {
                "id": i.asset_id,
                "item_id": i.id,
                "name": i.asset.name,
                "type": i.asset.media_type,
                "url": i.asset.public_url,
                "mime_type": i.asset.mime_type,
                "duration_seconds": i.duration_seconds or i.asset.duration_seconds or 10,
            }
            for i in items
        ]

    def _clear_default(self, store_id: str) -> None:
        for row in self.db.scalars(select(Playlist).where(Playlist.store_id == store_id, Playlist.is_default.is_(True))):
            row.is_default = False

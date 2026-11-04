from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.modules.queue.models.entities import Display
from app.modules.signage.models import Channel, MediaAsset, Playlist, PlaylistItem, Schedule
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


def _items_active(pl: Playlist) -> list[PlaylistItem]:
    return sorted([i for i in (pl.items or []) if i.active], key=lambda x: x.position)


def _total_duration(items: list[PlaylistItem]) -> int:
    total = 0
    for i in items:
        # Same rule as resolve_for_store / player
        total += int(i.duration_seconds or (i.asset.duration_seconds if i.asset else None) or 10)
    return total


def playlist_to_dict(
    pl: Playlist,
    *,
    include_items: bool = True,
    usage: dict[str, int] | None = None,
) -> dict[str, Any]:
    items = _items_active(pl) if include_items else []
    item_dicts = [item_to_dict(i) for i in items] if include_items else []
    data: dict[str, Any] = {
        "id": pl.id,
        "store_id": pl.store_id,
        "name": pl.name,
        "description": pl.description,
        "active": pl.active,
        "is_default": pl.is_default,
        "created_at": pl.created_at.isoformat() if pl.created_at else None,
        "updated_at": pl.updated_at.isoformat() if pl.updated_at else None,
        "items": item_dicts,
        "item_count": len(items) if include_items else None,
        "total_duration_seconds": _total_duration(items) if include_items else None,
    }
    if usage is not None:
        data["usage"] = usage
        data["usage_count"] = usage.get("usage_count", 0)
    return data


class PlaylistService:
    def __init__(self, db: Session):
        self.db = db

    def _usage_for(self, playlist_id: str) -> dict[str, int]:
        channels = int(
            self.db.scalar(
                select(func.count())
                .select_from(Channel)
                .where(Channel.default_playlist_id == playlist_id, Channel.active.is_(True))
            )
            or 0
        )
        schedules = int(
            self.db.scalar(
                select(func.count())
                .select_from(Schedule)
                .where(Schedule.playlist_id == playlist_id, Schedule.active.is_(True))
            )
            or 0
        )
        displays = int(
            self.db.scalar(
                select(func.count())
                .select_from(Display)
                .where(Display.playlist_id == playlist_id, Display.active.is_(True))
            )
            or 0
        )
        return {
            "channel_count": channels,
            "schedule_count": schedules,
            "display_count": displays,
            "usage_count": channels + schedules + displays,
        }

    def _usage_map(self, playlist_ids: list[str]) -> dict[str, dict[str, int]]:
        if not playlist_ids:
            return {}
        # Initialize zeros
        out = {
            pid: {"channel_count": 0, "schedule_count": 0, "display_count": 0, "usage_count": 0}
            for pid in playlist_ids
        }
        for pid, cnt in self.db.execute(
            select(Channel.default_playlist_id, func.count())
            .where(Channel.default_playlist_id.in_(playlist_ids), Channel.active.is_(True))
            .group_by(Channel.default_playlist_id)
        ):
            if pid in out:
                out[pid]["channel_count"] = int(cnt)
        for pid, cnt in self.db.execute(
            select(Schedule.playlist_id, func.count())
            .where(Schedule.playlist_id.in_(playlist_ids), Schedule.active.is_(True))
            .group_by(Schedule.playlist_id)
        ):
            if pid in out:
                out[pid]["schedule_count"] = int(cnt)
        for pid, cnt in self.db.execute(
            select(Display.playlist_id, func.count())
            .where(Display.playlist_id.in_(playlist_ids), Display.active.is_(True))
            .group_by(Display.playlist_id)
        ):
            if pid in out:
                out[pid]["display_count"] = int(cnt)
        for pid, u in out.items():
            u["usage_count"] = u["channel_count"] + u["schedule_count"] + u["display_count"]
        return out

    def _load(self, playlist_id: str, *, store_id: str | None = None) -> Playlist:
        pl = self.db.scalar(
            select(Playlist)
            .options(joinedload(Playlist.items).joinedload(PlaylistItem.asset))
            .where(Playlist.id == playlist_id)
        )
        if not pl:
            raise NotFoundError("Playlist não encontrada")
        if store_id and pl.store_id != store_id:
            raise ForbiddenError("Playlist não pertence à loja")
        return pl

    def list_playlists(self, store_id: str | None = None, active_only: bool = True) -> list[dict[str, Any]]:
        stmt = select(Playlist).options(
            joinedload(Playlist.items).joinedload(PlaylistItem.asset)
        ).order_by(Playlist.name)
        if store_id:
            stmt = stmt.where(Playlist.store_id == store_id)
        if active_only:
            stmt = stmt.where(Playlist.active.is_(True))
        rows = list(self.db.scalars(stmt).unique().all())
        usage = self._usage_map([p.id for p in rows])
        return [playlist_to_dict(p, usage=usage.get(p.id)) for p in rows]

    def get(self, playlist_id: str, *, store_id: str | None = None) -> dict[str, Any]:
        pl = self._load(playlist_id, store_id=store_id)
        return playlist_to_dict(pl, usage=self._usage_for(pl.id))

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
        return playlist_to_dict(self._load(pl.id), usage=self._usage_for(pl.id))

    def update(
        self,
        playlist_id: str,
        *,
        store_id: str | None = None,
        name: str | None = None,
        description: str | None = None,
        active: bool | None = None,
        is_default: bool | None = None,
    ) -> dict[str, Any]:
        pl = self._load(playlist_id, store_id=store_id)
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
        return playlist_to_dict(self._load(playlist_id), usage=self._usage_for(playlist_id))

    def delete(self, playlist_id: str, *, store_id: str | None = None) -> dict[str, Any]:
        pl = self._load(playlist_id, store_id=store_id)
        usage = self._usage_for(pl.id)
        if usage["usage_count"] > 0:
            parts = []
            if usage["channel_count"]:
                parts.append(f"{usage['channel_count']} canal(is)")
            if usage["schedule_count"]:
                parts.append(f"{usage['schedule_count']} programação(ões)")
            if usage["display_count"]:
                parts.append(f"{usage['display_count']} display(s)")
            raise ConflictError(
                "Esta playlist está em uso ("
                + ", ".join(parts)
                + "). Remova a associação antes de excluir."
            )
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
        store_id: str | None = None,
    ) -> dict[str, Any]:
        pl = self._load(playlist_id, store_id=store_id)
        asset = self.db.get(MediaAsset, asset_id)
        if not asset or not asset.active:
            raise NotFoundError("Mídia não encontrada")
        if asset.store_id != pl.store_id:
            raise ValidationError("Mídia pertence a outra loja")

        active = [i for i in pl.items if i.active]
        if position is None:
            position = max((i.position for i in active), default=-1) + 1
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
        return playlist_to_dict(self._load(playlist_id), usage=self._usage_for(playlist_id))

    def add_items(
        self,
        playlist_id: str,
        *,
        asset_ids: list[str],
        store_id: str | None = None,
    ) -> dict[str, Any]:
        """Add multiple assets in selection order (same asset may repeat)."""
        if not asset_ids:
            raise ValidationError("Nenhum conteúdo selecionado")
        pl = self._load(playlist_id, store_id=store_id)
        for asset_id in asset_ids:
            # reload positions each time via add_item internals without double commit cost —
            # reuse add_item which commits; acceptable for MVP volumes
            self.add_item(playlist_id, asset_id=asset_id, store_id=store_id)
        return playlist_to_dict(self._load(pl.id), usage=self._usage_for(pl.id))

    def update_item(
        self,
        playlist_id: str,
        item_id: str,
        *,
        duration_seconds: int | None = None,
        active: bool | None = None,
        store_id: str | None = None,
    ) -> dict[str, Any]:
        pl = self._load(playlist_id, store_id=store_id)
        item = next((i for i in pl.items if i.id == item_id), None)
        if not item:
            raise NotFoundError("Item da playlist não encontrado")
        if duration_seconds is not None:
            if int(duration_seconds) < 1:
                raise ValidationError("Duração deve ser pelo menos 1 segundo")
            item.duration_seconds = max(1, int(duration_seconds))
        if active is not None:
            item.active = active
        self.db.commit()
        return playlist_to_dict(self._load(playlist_id), usage=self._usage_for(playlist_id))

    def remove_item(
        self, playlist_id: str, item_id: str, *, store_id: str | None = None
    ) -> dict[str, Any]:
        pl = self._load(playlist_id, store_id=store_id)
        item = next((i for i in pl.items if i.id == item_id), None)
        if not item:
            raise NotFoundError("Item da playlist não encontrado")
        item.active = False
        active = sorted(
            [i for i in pl.items if i.active and i.id != item_id], key=lambda x: x.position
        )
        for idx, i in enumerate(active):
            i.position = idx
        self.db.commit()
        return playlist_to_dict(self._load(playlist_id), usage=self._usage_for(playlist_id))

    def reorder(
        self, playlist_id: str, item_ids: list[str], *, store_id: str | None = None
    ) -> dict[str, Any]:
        pl = self._load(playlist_id, store_id=store_id)
        active = {i.id: i for i in pl.items if i.active}
        if set(item_ids) != set(active.keys()):
            raise ValidationError("Lista de itens incompleta ou inválida para reordenação")
        for idx, item_id in enumerate(item_ids):
            active[item_id].position = idx
        self.db.commit()
        return playlist_to_dict(self._load(playlist_id), usage=self._usage_for(playlist_id))

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
        items = sorted(
            [i for i in pl.items if i.active and i.asset and i.asset.active],
            key=lambda x: x.position,
        )
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
        for row in self.db.scalars(
            select(Playlist).where(Playlist.store_id == store_id, Playlist.is_default.is_(True))
        ):
            row.is_default = False

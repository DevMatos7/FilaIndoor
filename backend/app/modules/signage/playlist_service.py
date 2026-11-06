from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.modules.dynamic_content.models import DynamicContent, DynamicRenderSnapshot
from app.modules.queue.models.entities import Display
from app.modules.signage.models import Channel, MediaAsset, Playlist, PlaylistItem, Schedule
from app.modules.signage.service import asset_to_dict


def _dynamic_effective_duration(db: Session, content: DynamicContent) -> int:
    """Compute DYNAMIC duration from current snapshot/config — never freeze forever."""
    latest = db.scalar(
        select(DynamicRenderSnapshot)
        .where(DynamicRenderSnapshot.dynamic_content_id == content.id)
        .order_by(DynamicRenderSnapshot.generated_at.desc())
        .limit(1)
    )
    if latest and isinstance(latest.payload, dict):
        pag = latest.payload.get("pagination") or {}
        total = pag.get("total_duration_seconds")
        if total is not None:
            return max(1, int(total))
        page_count = int(pag.get("page_count") or latest.page_count or 1)
        page_dur = int(pag.get("page_duration_seconds") or 8)
        return max(1, page_count * page_dur)

    cfg = content.config or {}
    page_dur = int(cfg.get("page_duration_seconds") or 8)
    mode = (cfg.get("duration_mode") or "FULL_CYCLE").upper()
    if mode == "FIXED":
        return max(1, int(cfg.get("total_duration_seconds") or page_dur))
    # FULL_CYCLE without snapshot: conservative 1 page
    return max(1, page_dur)


def item_to_dict(item: PlaylistItem) -> dict[str, Any]:
    asset = item.asset
    item_type = (item.item_type or "MEDIA").upper()
    return {
        "id": item.id,
        "playlist_id": item.playlist_id,
        "item_type": item_type,
        "asset_id": item.asset_id,
        "dynamic_content_id": item.dynamic_content_id,
        "position": item.position,
        "duration_seconds": item.duration_seconds,
        "duration_source": getattr(item, "duration_source", None) or "SOURCE",
        "active": item.active,
        "asset": asset_to_dict(asset) if asset else None,
        "dynamic_content": None,
    }


def _items_active(pl: Playlist) -> list[PlaylistItem]:
    return sorted([i for i in (pl.items or []) if i.active], key=lambda x: x.position)


def _item_duration(db: Session, item: PlaylistItem, content_map: dict[str, DynamicContent] | None = None) -> int:
    item_type = (item.item_type or "MEDIA").upper()
    if item_type == "DYNAMIC":
        source = (getattr(item, "duration_source", None) or "SOURCE").upper()
        if source == "OVERRIDE":
            return max(1, int(item.duration_seconds or 10))
        content = None
        if content_map and item.dynamic_content_id:
            content = content_map.get(item.dynamic_content_id)
        if content is None and item.dynamic_content_id:
            content = db.get(DynamicContent, item.dynamic_content_id)
        if content:
            return _dynamic_effective_duration(db, content)
        return max(1, int(item.duration_seconds or 10))
    # MEDIA — preserve historical semantics
    return int(item.duration_seconds or (item.asset.duration_seconds if item.asset else None) or 10)


def _total_duration(db: Session, items: list[PlaylistItem], content_map: dict[str, DynamicContent] | None = None) -> int:
    return sum(_item_duration(db, i, content_map) for i in items)


def playlist_to_dict(
    pl: Playlist,
    *,
    db: Session | None = None,
    include_items: bool = True,
    usage: dict[str, int] | None = None,
) -> dict[str, Any]:
    items = _items_active(pl) if include_items else []
    content_map: dict[str, DynamicContent] = {}
    if db is not None and include_items:
        dc_ids = [i.dynamic_content_id for i in items if i.dynamic_content_id]
        if dc_ids:
            for row in db.scalars(select(DynamicContent).where(DynamicContent.id.in_(dc_ids))).all():
                content_map[row.id] = row

    item_dicts = []
    if include_items:
        for i in items:
            d = item_to_dict(i)
            if i.dynamic_content_id and i.dynamic_content_id in content_map:
                dc = content_map[i.dynamic_content_id]
                latest = None
                if db is not None:
                    latest = db.scalar(
                        select(DynamicRenderSnapshot)
                        .where(DynamicRenderSnapshot.dynamic_content_id == dc.id)
                        .order_by(DynamicRenderSnapshot.generated_at.desc())
                        .limit(1)
                    )
                d["dynamic_content"] = {
                    "id": dc.id,
                    "name": dc.name,
                    "content_type": dc.content_type,
                    "status": (latest.payload or {}).get("status") if latest else None,
                    "page_count": latest.page_count if latest else None,
                    "item_count": latest.item_count if latest else None,
                    "total_duration_seconds": _dynamic_effective_duration(db, dc) if db else None,
                }
                # Reflect SOURCE duration for UI
                if db is not None and (getattr(i, "duration_source", None) or "SOURCE").upper() == "SOURCE":
                    d["effective_duration_seconds"] = _item_duration(db, i, content_map)
            elif i.asset:
                d["effective_duration_seconds"] = _item_duration(db, i, content_map) if db else i.duration_seconds
            item_dicts.append(d)

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
        "total_duration_seconds": _total_duration(db, items, content_map) if include_items and db else (
            sum(int(i.duration_seconds or 10) for i in items) if include_items else None
        ),
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
        usage = {
            pid: {"channel_count": 0, "schedule_count": 0, "display_count": 0, "usage_count": 0}
            for pid in playlist_ids
        }
        if not playlist_ids:
            return usage
        for row in self.db.execute(
            select(Channel.default_playlist_id, func.count())
            .where(Channel.default_playlist_id.in_(playlist_ids), Channel.active.is_(True))
            .group_by(Channel.default_playlist_id)
        ):
            usage[row[0]]["channel_count"] = int(row[1])
        for row in self.db.execute(
            select(Schedule.playlist_id, func.count())
            .where(Schedule.playlist_id.in_(playlist_ids), Schedule.active.is_(True))
            .group_by(Schedule.playlist_id)
        ):
            usage[row[0]]["schedule_count"] = int(row[1])
        for row in self.db.execute(
            select(Display.playlist_id, func.count())
            .where(Display.playlist_id.in_(playlist_ids), Display.active.is_(True))
            .group_by(Display.playlist_id)
        ):
            if row[0]:
                usage[row[0]]["display_count"] = int(row[1])
        for u in usage.values():
            u["usage_count"] = u["channel_count"] + u["schedule_count"] + u["display_count"]
        return usage

    def _load(self, playlist_id: str, store_id: str | None = None) -> Playlist:
        pl = self.db.scalar(
            select(Playlist)
            .options(joinedload(Playlist.items).joinedload(PlaylistItem.asset))
            .where(Playlist.id == playlist_id)
        )
        if not pl or not pl.active:
            raise NotFoundError("Playlist não encontrada")
        if store_id and pl.store_id != store_id:
            raise ForbiddenError("Playlist de outra loja")
        return pl

    def list_playlists(self, store_id: str | None = None, active_only: bool = True) -> list[dict[str, Any]]:
        stmt = select(Playlist).options(joinedload(Playlist.items).joinedload(PlaylistItem.asset))
        if store_id:
            stmt = stmt.where(Playlist.store_id == store_id)
        if active_only:
            stmt = stmt.where(Playlist.active.is_(True))
        rows = list(self.db.scalars(stmt.order_by(Playlist.name)).unique().all())
        usage = self._usage_map([p.id for p in rows])
        return [playlist_to_dict(p, db=self.db, usage=usage.get(p.id)) for p in rows]

    def get(self, playlist_id: str, store_id: str | None = None) -> dict[str, Any]:
        pl = self._load(playlist_id, store_id=store_id)
        return playlist_to_dict(pl, db=self.db, usage=self._usage_for(playlist_id))

    def create(
        self,
        *,
        store_id: str,
        name: str,
        description: str | None = None,
        is_default: bool = False,
    ) -> dict[str, Any]:
        if is_default:
            self._clear_default(store_id)
        pl = Playlist(store_id=store_id, name=name.strip(), description=description, is_default=is_default)
        self.db.add(pl)
        self.db.commit()
        return playlist_to_dict(self._load(pl.id), db=self.db, usage=self._usage_for(pl.id))

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
            pl.name = name.strip()
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
        return playlist_to_dict(self._load(playlist_id), db=self.db, usage=self._usage_for(playlist_id))

    def delete(self, playlist_id: str, *, store_id: str | None = None) -> dict[str, Any]:
        pl = self._load(playlist_id, store_id=store_id)
        usage = self._usage_for(playlist_id)
        if usage["usage_count"] > 0:
            parts = []
            if usage["channel_count"]:
                parts.append(f"{usage['channel_count']} canal(is)")
            if usage["schedule_count"]:
                parts.append(f"{usage['schedule_count']} agenda(s)")
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
        asset_id: str | None = None,
        dynamic_content_id: str | None = None,
        item_type: str | None = None,
        duration_seconds: int | None = None,
        duration_source: str | None = None,
        position: int | None = None,
        store_id: str | None = None,
    ) -> dict[str, Any]:
        pl = self._load(playlist_id, store_id=store_id)
        resolved_type = (item_type or ("DYNAMIC" if dynamic_content_id else "MEDIA")).upper()
        if resolved_type not in {"MEDIA", "DYNAMIC"}:
            raise ValidationError("item_type inválido")

        if resolved_type == "MEDIA":
            if not asset_id or dynamic_content_id:
                raise ValidationError("MEDIA exige asset_id e não permite dynamic_content_id")
            asset = self.db.get(MediaAsset, asset_id)
            if not asset or not asset.active:
                raise NotFoundError("Mídia não encontrada")
            if asset.store_id != pl.store_id:
                raise ValidationError("Mídia pertence a outra loja")
            duration = duration_seconds if duration_seconds is not None else (asset.duration_seconds or 10)
            item = PlaylistItem(
                playlist_id=pl.id,
                item_type="MEDIA",
                asset_id=asset.id,
                dynamic_content_id=None,
                position=0,
                duration_seconds=max(1, int(duration)),
                duration_source="OVERRIDE" if duration_seconds is not None else "SOURCE",
            )
        else:
            if not dynamic_content_id or asset_id:
                raise ValidationError("DYNAMIC exige dynamic_content_id e não permite asset_id")
            content = self.db.get(DynamicContent, dynamic_content_id)
            if not content or not content.active:
                raise NotFoundError("Conteúdo dinâmico não encontrado")
            if content.store_id != pl.store_id:
                raise ValidationError("Conteúdo dinâmico pertence a outra loja")
            # MVP: SOURCE only for DYNAMIC
            source = (duration_source or "SOURCE").upper()
            if source not in {"SOURCE", "OVERRIDE"}:
                raise ValidationError("duration_source inválido")
            if source == "OVERRIDE" and duration_seconds is None:
                raise ValidationError("OVERRIDE exige duration_seconds")
            eff = (
                max(1, int(duration_seconds))
                if source == "OVERRIDE"
                else _dynamic_effective_duration(self.db, content)
            )
            item = PlaylistItem(
                playlist_id=pl.id,
                item_type="DYNAMIC",
                asset_id=None,
                dynamic_content_id=content.id,
                position=0,
                duration_seconds=eff,
                duration_source=source,
            )

        active = [i for i in pl.items if i.active]
        if position is None:
            position = max((i.position for i in active), default=-1) + 1
        else:
            for i in active:
                if i.position >= position:
                    i.position += 1
        item.position = position
        self.db.add(item)
        self.db.commit()
        return playlist_to_dict(self._load(playlist_id), db=self.db, usage=self._usage_for(playlist_id))

    def add_items(
        self,
        playlist_id: str,
        *,
        asset_ids: list[str] | None = None,
        items: list[dict[str, Any]] | None = None,
        store_id: str | None = None,
    ) -> dict[str, Any]:
        """Bulk add — preserves asset_ids contract; optional typed items."""
        if items:
            if not items:
                raise ValidationError("Nenhum conteúdo selecionado")
            for entry in items:
                self.add_item(
                    playlist_id,
                    asset_id=entry.get("asset_id"),
                    dynamic_content_id=entry.get("dynamic_content_id"),
                    item_type=entry.get("item_type"),
                    duration_seconds=entry.get("duration_seconds"),
                    duration_source=entry.get("duration_source"),
                    store_id=store_id,
                )
            return playlist_to_dict(self._load(playlist_id), db=self.db, usage=self._usage_for(playlist_id))

        if not asset_ids:
            raise ValidationError("Nenhum conteúdo selecionado")
        for asset_id in asset_ids:
            self.add_item(playlist_id, asset_id=asset_id, item_type="MEDIA", store_id=store_id)
        return playlist_to_dict(self._load(playlist_id), db=self.db, usage=self._usage_for(playlist_id))

    def update_item(
        self,
        playlist_id: str,
        item_id: str,
        *,
        duration_seconds: int | None = None,
        duration_source: str | None = None,
        active: bool | None = None,
        store_id: str | None = None,
    ) -> dict[str, Any]:
        pl = self._load(playlist_id, store_id=store_id)
        item = next((i for i in pl.items if i.id == item_id), None)
        if not item:
            raise NotFoundError("Item da playlist não encontrado")
        if duration_source is not None:
            src = duration_source.upper()
            if src not in {"SOURCE", "OVERRIDE"}:
                raise ValidationError("duration_source inválido")
            if (item.item_type or "MEDIA").upper() == "DYNAMIC" and src == "OVERRIDE":
                # allowed but MVP studio defaults to SOURCE — still validate
                pass
            item.duration_source = src
        if duration_seconds is not None:
            if int(duration_seconds) < 1:
                raise ValidationError("Duração deve ser pelo menos 1 segundo")
            item.duration_seconds = max(1, int(duration_seconds))
            if (item.item_type or "MEDIA").upper() == "DYNAMIC":
                item.duration_source = "OVERRIDE"
        if active is not None:
            item.active = active
        self.db.commit()
        return playlist_to_dict(self._load(playlist_id), db=self.db, usage=self._usage_for(playlist_id))

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
        return playlist_to_dict(self._load(playlist_id), db=self.db, usage=self._usage_for(playlist_id))

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
        return playlist_to_dict(self._load(playlist_id), db=self.db, usage=self._usage_for(playlist_id))

    def resolve_for_store(self, store_id: str, playlist_id: str | None = None) -> list[dict[str, Any]]:
        """Itens prontos para o player TV (MEDIA + DYNAMIC)."""
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

        active_items = sorted([i for i in pl.items if i.active], key=lambda x: x.position)
        out: list[dict[str, Any]] = []
        for i in active_items:
            item_type = (i.item_type or "MEDIA").upper()
            if item_type == "MEDIA":
                if not i.asset or not i.asset.active:
                    continue
                out.append(
                    {
                        "id": i.asset_id,
                        "item_id": i.id,
                        "item_type": "MEDIA",
                        "name": i.asset.name,
                        "type": i.asset.media_type,
                        "url": i.asset.public_url,
                        "mime_type": i.asset.mime_type,
                        "duration_seconds": i.duration_seconds or i.asset.duration_seconds or 10,
                    }
                )
            elif item_type == "DYNAMIC":
                if not i.dynamic_content_id:
                    continue
                content = self.db.get(DynamicContent, i.dynamic_content_id)
                if not content or not content.active or content.store_id != store_id:
                    continue
                duration = _item_duration(self.db, i, {content.id: content})
                out.append(
                    {
                        "id": content.id,
                        "item_id": i.id,
                        "item_type": "DYNAMIC",
                        "name": content.name,
                        "type": "DYNAMIC",
                        "url": "",
                        "mime_type": None,
                        "duration_seconds": duration,
                        "dynamic_content": {
                            "id": content.id,
                            "content_type": content.content_type,
                            "name": content.name,
                        },
                    }
                )
        return out

    def _clear_default(self, store_id: str) -> None:
        for row in self.db.scalars(
            select(Playlist).where(Playlist.store_id == store_id, Playlist.is_default.is_(True))
        ):
            row.is_default = False

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.queue.models.entities import utcnow
from app.modules.signage.models import Channel, Schedule, ScreenGroup
from app.modules.signage.playlist_service import PlaylistService

PRIORITY_WEIGHT = {"EMERGENCY": 100, "HIGH": 50, "NORMAL": 10}


def _parse_days(raw: str) -> set[int]:
    days: set[int] = set()
    for part in (raw or "").split(","):
        part = part.strip()
        if part.isdigit():
            days.add(int(part))
    return days or {0, 1, 2, 3, 4, 5, 6}


def _parse_time(value: str | time) -> time:
    if isinstance(value, time):
        return value
    parts = value.strip().split(":")
    return time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)


def _parse_date(value: str | date | None) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def schedule_matches(sch: Schedule, when: datetime) -> bool:
    if not sch.active:
        return False
    d = when.date()
    t = when.time().replace(second=0, microsecond=0)
    if sch.start_date and d < sch.start_date:
        return False
    if sch.end_date and d > sch.end_date:
        return False
    if when.weekday() not in _parse_days(sch.days_of_week):
        return False
    start = sch.start_time.replace(second=0, microsecond=0)
    end = sch.end_time.replace(second=0, microsecond=0)
    if start <= end:
        return start <= t <= end
    # atravessa meia-noite
    return t >= start or t <= end


def schedule_to_dict(sch: Schedule) -> dict[str, Any]:
    return {
        "id": sch.id,
        "channel_id": sch.channel_id,
        "playlist_id": sch.playlist_id,
        "name": sch.name,
        "start_date": sch.start_date.isoformat() if sch.start_date else None,
        "end_date": sch.end_date.isoformat() if sch.end_date else None,
        "start_time": sch.start_time.strftime("%H:%M"),
        "end_time": sch.end_time.strftime("%H:%M"),
        "days_of_week": [int(x) for x in sorted(_parse_days(sch.days_of_week))],
        "priority": sch.priority,
        "priority_weight": PRIORITY_WEIGHT.get(sch.priority, 10),
        "active": sch.active,
        "playlist_name": sch.playlist.name if sch.playlist else None,
    }


def channel_to_dict(ch: Channel, *, include_schedules: bool = True) -> dict[str, Any]:
    return {
        "id": ch.id,
        "store_id": ch.store_id,
        "name": ch.name,
        "layout": ch.layout,
        "default_playlist_id": ch.default_playlist_id,
        "active": ch.active,
        "schedules": [schedule_to_dict(s) for s in ch.schedules] if include_schedules else [],
        "groups": [
            {"id": g.id, "name": g.name, "channel_id": g.channel_id, "active": g.active}
            for g in (ch.groups or [])
            if g.active
        ],
    }


class ScheduleService:
    def __init__(self, db: Session):
        self.db = db

    def list_channels(self, store_id: str | None = None) -> list[dict[str, Any]]:
        stmt = (
            select(Channel)
            .options(joinedload(Channel.schedules).joinedload(Schedule.playlist), joinedload(Channel.groups))
            .where(Channel.active.is_(True))
            .order_by(Channel.name)
        )
        if store_id:
            stmt = stmt.where(Channel.store_id == store_id)
        return [channel_to_dict(c) for c in self.db.scalars(stmt).unique().all()]

    def get_channel(self, channel_id: str) -> dict[str, Any]:
        return channel_to_dict(self._channel(channel_id))

    def create_channel(
        self,
        *,
        store_id: str,
        name: str,
        layout: str = "queue_media_split",
        default_playlist_id: str | None = None,
    ) -> dict[str, Any]:
        ch = Channel(
            store_id=store_id,
            name=name.strip(),
            layout=layout or "queue_media_split",
            default_playlist_id=default_playlist_id,
        )
        self.db.add(ch)
        self.db.commit()
        return self.get_channel(ch.id)

    def update_channel(self, channel_id: str, **fields: Any) -> dict[str, Any]:
        ch = self._channel(channel_id)
        for key, value in fields.items():
            if value is None and key not in {"default_playlist_id"}:
                continue
            if hasattr(ch, key):
                setattr(ch, key, value)
        self.db.commit()
        return self.get_channel(channel_id)

    def create_group(self, *, store_id: str, channel_id: str, name: str) -> dict[str, Any]:
        self._channel(channel_id)
        g = ScreenGroup(store_id=store_id, channel_id=channel_id, name=name.strip())
        self.db.add(g)
        self.db.commit()
        self.db.refresh(g)
        return {"id": g.id, "store_id": g.store_id, "channel_id": g.channel_id, "name": g.name, "active": g.active}

    def create_schedule(self, *, channel_id: str, playlist_id: str, **fields: Any) -> dict[str, Any]:
        self._channel(channel_id)
        priority = (fields.get("priority") or "NORMAL").upper()
        if priority not in PRIORITY_WEIGHT:
            raise ValidationError("Prioridade inválida (NORMAL|HIGH|EMERGENCY)")
        days = fields.get("days_of_week")
        if isinstance(days, list):
            days_csv = ",".join(str(int(d)) for d in days)
        else:
            days_csv = days or "0,1,2,3,4,5,6"
        sch = Schedule(
            channel_id=channel_id,
            playlist_id=playlist_id,
            name=(fields.get("name") or "Agenda").strip(),
            start_date=_parse_date(fields.get("start_date")),
            end_date=_parse_date(fields.get("end_date")),
            start_time=_parse_time(fields.get("start_time") or "00:00"),
            end_time=_parse_time(fields.get("end_time") or "23:59"),
            days_of_week=days_csv,
            priority=priority,
        )
        self.db.add(sch)
        self.db.commit()
        return schedule_to_dict(self._schedule(sch.id))

    def update_schedule(self, schedule_id: str, **fields: Any) -> dict[str, Any]:
        sch = self._schedule(schedule_id)
        if "name" in fields and fields["name"] is not None:
            sch.name = fields["name"].strip()
        if "playlist_id" in fields and fields["playlist_id"]:
            sch.playlist_id = fields["playlist_id"]
        if "priority" in fields and fields["priority"]:
            p = fields["priority"].upper()
            if p not in PRIORITY_WEIGHT:
                raise ValidationError("Prioridade inválida")
            sch.priority = p
        if "active" in fields and fields["active"] is not None:
            sch.active = fields["active"]
        if "start_date" in fields:
            sch.start_date = _parse_date(fields["start_date"])
        if "end_date" in fields:
            sch.end_date = _parse_date(fields["end_date"])
        if "start_time" in fields and fields["start_time"]:
            sch.start_time = _parse_time(fields["start_time"])
        if "end_time" in fields and fields["end_time"]:
            sch.end_time = _parse_time(fields["end_time"])
        if "days_of_week" in fields and fields["days_of_week"] is not None:
            days = fields["days_of_week"]
            sch.days_of_week = ",".join(str(int(d)) for d in days) if isinstance(days, list) else str(days)
        self.db.commit()
        return schedule_to_dict(self._schedule(schedule_id))

    def delete_schedule(self, schedule_id: str) -> dict[str, Any]:
        sch = self._schedule(schedule_id)
        sch.active = False
        self.db.commit()
        return {"id": schedule_id, "active": False}

    def active_at(self, channel_id: str, when: datetime | None = None) -> dict[str, Any]:
        when = when or utcnow()
        ch = self._channel(channel_id)
        matching = [s for s in ch.schedules if schedule_matches(s, when)]
        conflicts = self._conflict_pairs(matching)
        if not matching:
            playlist_id = ch.default_playlist_id
            return {
                "channel_id": channel_id,
                "at": when.isoformat(),
                "schedule": None,
                "playlist_id": playlist_id,
                "source": "channel_default" if playlist_id else "none",
                "conflicts": [],
            }
        matching.sort(key=lambda s: (-PRIORITY_WEIGHT.get(s.priority, 10), s.name))
        winner = matching[0]
        return {
            "channel_id": channel_id,
            "at": when.isoformat(),
            "schedule": schedule_to_dict(winner),
            "playlist_id": winner.playlist_id,
            "source": "schedule",
            "matching_count": len(matching),
            "conflicts": conflicts,
        }

    def list_conflicts(self, channel_id: str, when: datetime | None = None) -> dict[str, Any]:
        when = when or utcnow()
        ch = self._channel(channel_id)
        matching = [s for s in ch.schedules if schedule_matches(s, when)]
        return {
            "channel_id": channel_id,
            "at": when.isoformat(),
            "matching": [schedule_to_dict(s) for s in matching],
            "conflicts": self._conflict_pairs(matching),
        }

    def resolve_playlist_for_display(
        self,
        *,
        store_id: str,
        channel_id: str | None,
        playlist_id: str | None,
        when: datetime | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Retorna (itens player, meta)."""
        when = when or utcnow()
        meta: dict[str, Any] = {"source": "none", "schedule": None, "conflicts": []}
        pl_svc = PlaylistService(self.db)
        chosen_playlist: str | None = None

        if channel_id:
            active = self.active_at(channel_id, when)
            meta = {
                "source": active["source"],
                "schedule": active.get("schedule"),
                "conflicts": active.get("conflicts") or [],
                "channel_id": channel_id,
            }
            chosen_playlist = active.get("playlist_id")

        if not chosen_playlist and playlist_id:
            chosen_playlist = playlist_id
            meta["source"] = "display_playlist"

        items = pl_svc.resolve_for_store(store_id, chosen_playlist) if chosen_playlist else pl_svc.resolve_for_store(store_id)
        if items and meta["source"] == "none":
            meta["source"] = "store_default"
        return items, meta

    def _conflict_pairs(self, matching: list[Schedule]) -> list[dict[str, Any]]:
        """Conflito = duas agendas com mesma prioridade ativas no mesmo instante."""
        by_prio: dict[str, list[Schedule]] = {}
        for s in matching:
            by_prio.setdefault(s.priority, []).append(s)
        conflicts = []
        for prio, rows in by_prio.items():
            if len(rows) > 1:
                conflicts.append(
                    {
                        "priority": prio,
                        "schedule_ids": [r.id for r in rows],
                        "names": [r.name for r in rows],
                        "message": f"{len(rows)} agendas {prio} sobrepostas — vence a primeira por nome",
                    }
                )
        return conflicts

    def _channel(self, channel_id: str) -> Channel:
        ch = self.db.scalar(
            select(Channel)
            .options(joinedload(Channel.schedules).joinedload(Schedule.playlist), joinedload(Channel.groups))
            .where(Channel.id == channel_id)
        )
        if not ch:
            raise NotFoundError("Canal não encontrado")
        return ch

    def _schedule(self, schedule_id: str) -> Schedule:
        sch = self.db.scalar(
            select(Schedule).options(joinedload(Schedule.playlist)).where(Schedule.id == schedule_id)
        )
        if not sch:
            raise NotFoundError("Agenda não encontrada")
        return sch

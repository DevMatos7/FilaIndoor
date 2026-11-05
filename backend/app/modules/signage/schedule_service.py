from __future__ import annotations

from datetime import date, datetime, timedelta, time
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.modules.queue.models.entities import Display, utcnow
from app.modules.signage.layout_service import LayoutService
from app.modules.signage.models import Channel, LayoutTemplate, Playlist, Schedule, ScreenGroup
from app.modules.signage.playlist_service import PlaylistService

PRIORITY_WEIGHT = {"EMERGENCY": 100, "HIGH": 50, "NORMAL": 10}
PRIORITY_LABELS = {
    "NORMAL": "Programação normal",
    "HIGH": "Prioritária",
    "EMERGENCY": "Emergencial",
}


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
    # atravessa meia-noite — suportado pelo domínio atual
    return t >= start or t <= end


def _dates_overlap(a: Schedule, b: Schedule) -> bool:
    a_start = a.start_date or date.min
    a_end = a.end_date or date.max
    b_start = b.start_date or date.min
    b_end = b.end_date or date.max
    return a_start <= b_end and b_start <= a_end


def _times_overlap(a: Schedule, b: Schedule) -> bool:
    """Interval overlap; overnight treated as [start,24h) U [0,end]."""

    def intervals(sch: Schedule) -> list[tuple[int, int]]:
        s = sch.start_time.hour * 60 + sch.start_time.minute
        e = sch.end_time.hour * 60 + sch.end_time.minute
        if s <= e:
            return [(s, e)]
        return [(s, 24 * 60), (0, e)]

    for s1, e1 in intervals(a):
        for s2, e2 in intervals(b):
            if s1 <= e2 and s2 <= e1:
                return True
    return False


def _structural_overlap(a: Schedule, b: Schedule) -> bool:
    if not a.active or not b.active:
        return False
    if not _dates_overlap(a, b):
        return False
    if not (_parse_days(a.days_of_week) & _parse_days(b.days_of_week)):
        return False
    return _times_overlap(a, b)


def schedule_to_dict(sch: Schedule, *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {
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
        "priority_label": PRIORITY_LABELS.get(sch.priority, sch.priority),
        "priority_weight": PRIORITY_WEIGHT.get(sch.priority, 10),
        "active": sch.active,
        "playlist_name": sch.playlist.name if sch.playlist else None,
        "overnight": sch.start_time > sch.end_time,
    }
    if extra:
        data.update(extra)
    return data


def channel_to_dict(
    ch: Channel,
    *,
    include_schedules: bool = True,
    layout_summary: dict[str, Any] | None = None,
    default_playlist_summary: dict[str, Any] | None = None,
    usage: dict[str, int] | None = None,
) -> dict[str, Any]:
    active_schedules = [s for s in (ch.schedules or []) if s.active]
    data: dict[str, Any] = {
        "id": ch.id,
        "store_id": ch.store_id,
        "name": ch.name,
        "layout": ch.layout,
        "layout_template_id": ch.layout_template_id,
        "default_playlist_id": ch.default_playlist_id,
        "active": ch.active,
        "schedule_count": len(active_schedules),
        "schedules": [schedule_to_dict(s) for s in active_schedules] if include_schedules else [],
        "groups": [
            {"id": g.id, "name": g.name, "channel_id": g.channel_id, "active": g.active}
            for g in (ch.groups or [])
            if g.active
        ],
    }
    if layout_summary is not None:
        data["layout_summary"] = layout_summary
    if default_playlist_summary is not None:
        data["default_playlist"] = default_playlist_summary
    if usage is not None:
        data["usage"] = usage
        data["usage_count"] = usage.get("usage_count", 0)
    return data


class ScheduleService:
    def __init__(self, db: Session):
        self.db = db

    def _assert_store(self, ch: Channel, store_id: str | None) -> None:
        if store_id and ch.store_id != store_id:
            raise ForbiddenError("Canal não pertence à loja")

    def _playlist_summary(self, playlist_id: str | None) -> dict[str, Any] | None:
        if not playlist_id:
            return None
        try:
            pl = PlaylistService(self.db).get(playlist_id)
            return {
                "id": pl["id"],
                "name": pl["name"],
                "item_count": pl.get("item_count") or 0,
                "total_duration_seconds": pl.get("total_duration_seconds") or 0,
            }
        except NotFoundError:
            return {"id": playlist_id, "name": None, "item_count": 0, "total_duration_seconds": 0}

    def _layout_summary(self, ch: Channel) -> dict[str, Any]:
        resolved = LayoutService(self.db).resolve_for_channel(channel=ch, store_id=ch.store_id)
        return {
            "layout_template_id": resolved.get("id") or ch.layout_template_id,
            "slug": resolved.get("slug"),
            "name": resolved.get("name") or ch.layout,
            "legacy_layout": ch.layout,
            "resolved_from": resolved.get("resolved_from"),
            "zones": [
                {
                    "type": z.get("type"),
                    "x": z.get("x"),
                    "y": z.get("y"),
                    "width": z.get("width"),
                    "height": z.get("height"),
                }
                for z in (resolved.get("zones") or [])
            ],
        }

    def _channel_usage(self, channel_id: str) -> dict[str, int]:
        displays = int(
            self.db.scalar(
                select(func.count()).select_from(Display).where(
                    Display.channel_id == channel_id, Display.active.is_(True)
                )
            )
            or 0
        )
        groups = int(
            self.db.scalar(
                select(func.count()).select_from(ScreenGroup).where(
                    ScreenGroup.channel_id == channel_id, ScreenGroup.active.is_(True)
                )
            )
            or 0
        )
        schedules = int(
            self.db.scalar(
                select(func.count()).select_from(Schedule).where(
                    Schedule.channel_id == channel_id, Schedule.active.is_(True)
                )
            )
            or 0
        )
        return {
            "display_count": displays,
            "group_count": groups,
            "schedule_count": schedules,
            "usage_count": displays + groups,
        }

    def _validate_playlist(self, *, store_id: str, playlist_id: str | None) -> None:
        if not playlist_id:
            return
        pl = self.db.get(Playlist, playlist_id)
        if not pl or not pl.active:
            raise NotFoundError("Playlist não encontrada")
        if pl.store_id != store_id:
            raise ValidationError("Playlist pertence a outra loja")

    def _validate_layout_template(self, *, store_id: str, template_id: str | None) -> None:
        if not template_id:
            return
        tpl = self.db.get(LayoutTemplate, template_id)
        if not tpl or not tpl.active:
            raise NotFoundError("Layout não encontrado")
        if tpl.store_id is not None and tpl.store_id != store_id:
            raise ValidationError("Layout pertence a outra loja")

    def list_channels(self, store_id: str | None = None) -> list[dict[str, Any]]:
        stmt = (
            select(Channel)
            .options(joinedload(Channel.schedules).joinedload(Schedule.playlist), joinedload(Channel.groups))
            .where(Channel.active.is_(True))
            .order_by(Channel.name)
        )
        if store_id:
            stmt = stmt.where(Channel.store_id == store_id)
        rows = list(self.db.scalars(stmt).unique().all())
        out = []
        for c in rows:
            out.append(
                channel_to_dict(
                    c,
                    layout_summary=self._layout_summary(c),
                    default_playlist_summary=self._playlist_summary(c.default_playlist_id),
                    usage=self._channel_usage(c.id),
                )
            )
        return out

    def get_channel(self, channel_id: str, *, store_id: str | None = None) -> dict[str, Any]:
        ch = self._channel(channel_id)
        self._assert_store(ch, store_id)
        return channel_to_dict(
            ch,
            layout_summary=self._layout_summary(ch),
            default_playlist_summary=self._playlist_summary(ch.default_playlist_id),
            usage=self._channel_usage(ch.id),
        )

    def create_channel(
        self,
        *,
        store_id: str,
        name: str,
        layout: str = "queue_media_split",
        layout_template_id: str | None = None,
        default_playlist_id: str | None = None,
    ) -> dict[str, Any]:
        self._validate_playlist(store_id=store_id, playlist_id=default_playlist_id)
        self._validate_layout_template(store_id=store_id, template_id=layout_template_id)
        ch = Channel(
            store_id=store_id,
            name=name.strip(),
            layout=layout or "queue_media_split",
            layout_template_id=layout_template_id,
            default_playlist_id=default_playlist_id,
        )
        self.db.add(ch)
        self.db.commit()
        return self.get_channel(ch.id)

    def update_channel(
        self, channel_id: str, *, store_id: str | None = None, **fields: Any
    ) -> dict[str, Any]:
        ch = self._channel(channel_id)
        self._assert_store(ch, store_id)
        if "default_playlist_id" in fields:
            self._validate_playlist(store_id=ch.store_id, playlist_id=fields.get("default_playlist_id"))
        if "layout_template_id" in fields:
            self._validate_layout_template(store_id=ch.store_id, template_id=fields.get("layout_template_id"))
        for key, value in fields.items():
            if value is None and key not in {"default_playlist_id", "layout_template_id"}:
                continue
            if hasattr(ch, key):
                setattr(ch, key, value)
        self.db.commit()
        return self.get_channel(channel_id)

    def delete_channel(self, channel_id: str, *, store_id: str | None = None) -> dict[str, Any]:
        ch = self._channel(channel_id)
        self._assert_store(ch, store_id)
        usage = self._channel_usage(channel_id)
        if usage["display_count"] or usage["group_count"]:
            parts = []
            if usage["display_count"]:
                parts.append(f"{usage['display_count']} display(s)")
            if usage["group_count"]:
                parts.append(f"{usage['group_count']} grupo(s) de tela")
            raise ConflictError(
                "Este canal está em uso (" + ", ".join(parts) + "). Remova as associações antes de excluir."
            )
        # soft-delete channel + soft-delete schedules
        for s in ch.schedules:
            s.active = False
        ch.active = False
        self.db.commit()
        return {"id": channel_id, "active": False}

    def create_group(self, *, store_id: str, channel_id: str, name: str) -> dict[str, Any]:
        ch = self._channel(channel_id)
        if ch.store_id != store_id:
            raise ForbiddenError("Canal não pertence à loja")
        g = ScreenGroup(store_id=store_id, channel_id=channel_id, name=name.strip())
        self.db.add(g)
        self.db.commit()
        self.db.refresh(g)
        return {"id": g.id, "store_id": g.store_id, "channel_id": g.channel_id, "name": g.name, "active": g.active}

    def create_schedule(self, *, channel_id: str, playlist_id: str, **fields: Any) -> dict[str, Any]:
        ch = self._channel(channel_id)
        self._validate_playlist(store_id=ch.store_id, playlist_id=playlist_id)
        priority = (fields.get("priority") or "NORMAL").upper()
        if priority not in PRIORITY_WEIGHT:
            raise ValidationError("Prioridade inválida (NORMAL|HIGH|EMERGENCY)")
        days = fields.get("days_of_week")
        if isinstance(days, list):
            if not days:
                raise ValidationError("Selecione ao menos um dia da semana")
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
        start_d = sch.start_date
        end_d = sch.end_date
        if start_d and end_d and end_d < start_d:
            raise ValidationError("Data final deve ser posterior ou igual à data inicial")
        self.db.add(sch)
        self.db.commit()
        return schedule_to_dict(
            self._schedule(sch.id),
            extra={"playlist_summary": self._playlist_summary(playlist_id)},
        )

    def update_schedule(self, schedule_id: str, **fields: Any) -> dict[str, Any]:
        sch = self._schedule(schedule_id)
        ch = self._channel(sch.channel_id)
        if "name" in fields and fields["name"] is not None:
            sch.name = fields["name"].strip()
        if "playlist_id" in fields and fields["playlist_id"]:
            self._validate_playlist(store_id=ch.store_id, playlist_id=fields["playlist_id"])
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
            if isinstance(days, list) and not days:
                raise ValidationError("Selecione ao menos um dia da semana")
            sch.days_of_week = ",".join(str(int(d)) for d in days) if isinstance(days, list) else str(days)
        if sch.start_date and sch.end_date and sch.end_date < sch.start_date:
            raise ValidationError("Data final deve ser posterior ou igual à data inicial")
        self.db.commit()
        return schedule_to_dict(
            self._schedule(schedule_id),
            extra={"playlist_summary": self._playlist_summary(sch.playlist_id)},
        )

    def delete_schedule(self, schedule_id: str) -> dict[str, Any]:
        sch = self._schedule(schedule_id)
        sch.active = False
        self.db.commit()
        return {"id": schedule_id, "active": False}

    def active_at(self, channel_id: str, when: datetime | None = None) -> dict[str, Any]:
        """Fonte de verdade compartilhada com o player (resolve_playlist_for_display)."""
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
                "playlist": self._playlist_summary(playlist_id),
                "source": "channel_default" if playlist_id else "none",
                "conflicts": [],
            }
        matching.sort(key=lambda s: (-PRIORITY_WEIGHT.get(s.priority, 10), s.name))
        winner = matching[0]
        return {
            "channel_id": channel_id,
            "at": when.isoformat(),
            "schedule": schedule_to_dict(winner, extra={"playlist_summary": self._playlist_summary(winner.playlist_id)}),
            "playlist_id": winner.playlist_id,
            "playlist": self._playlist_summary(winner.playlist_id),
            "source": "schedule",
            "matching_count": len(matching),
            "conflicts": conflicts,
        }

    def next_at(self, channel_id: str, when: datetime | None = None) -> dict[str, Any] | None:
        """Próximo início de agenda após `when` (até 7 dias)."""
        when = when or utcnow()
        ch = self._channel(channel_id)
        current = self.active_at(channel_id, when)
        current_id = (current.get("schedule") or {}).get("id")
        candidates: list[tuple[datetime, Schedule]] = []
        for offset in range(0, 8):
            day = when.date() + timedelta(days=offset)
            weekday = day.weekday()
            for sch in ch.schedules:
                if not sch.active:
                    continue
                if sch.start_date and day < sch.start_date:
                    continue
                if sch.end_date and day > sch.end_date:
                    continue
                if weekday not in _parse_days(sch.days_of_week):
                    continue
                start_dt = datetime.combine(day, sch.start_time.replace(second=0, microsecond=0))
                if start_dt <= when:
                    continue
                if current_id and sch.id == current_id and schedule_matches(sch, when):
                    # still the current block — skip its ongoing start
                    continue
                candidates.append((start_dt, sch))
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0])
        start_dt, sch = candidates[0]
        return {
            "at": start_dt.isoformat(),
            "schedule": schedule_to_dict(sch, extra={"playlist_summary": self._playlist_summary(sch.playlist_id)}),
            "playlist_id": sch.playlist_id,
            "playlist": self._playlist_summary(sch.playlist_id),
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

    def analyze_conflicts(self, channel_id: str) -> list[dict[str, Any]]:
        """Conflitos estruturais entre agendas ativas (para timeline/UI)."""
        ch = self._channel(channel_id)
        active = [s for s in ch.schedules if s.active]
        out: list[dict[str, Any]] = []
        for i, a in enumerate(active):
            for b in active[i + 1 :]:
                if not _structural_overlap(a, b):
                    continue
                wa = PRIORITY_WEIGHT.get(a.priority, 10)
                wb = PRIORITY_WEIGHT.get(b.priority, 10)
                if wa == wb:
                    kind = "AMBIGUOUS"
                    message = "Conflito de horário — mesma prioridade"
                else:
                    kind = "RESOLVED_BY_PRIORITY"
                    winner = a if wa > wb else b
                    message = f"Prioridade define a exibição ({PRIORITY_LABELS.get(winner.priority, winner.priority)})"
                out.append(
                    {
                        "kind": kind,
                        "message": message,
                        "schedule_ids": [a.id, b.id],
                        "names": [a.name, b.name],
                        "priorities": [a.priority, b.priority],
                    }
                )
        return out

    def programming_overview(
        self, channel_id: str, *, store_id: str | None = None, when: datetime | None = None
    ) -> dict[str, Any]:
        when = when or utcnow()
        ch = self._channel(channel_id)
        self._assert_store(ch, store_id)
        current = self.active_at(channel_id, when)
        nxt = self.next_at(channel_id, when)
        conflicts = self.analyze_conflicts(channel_id)
        schedules = [
            schedule_to_dict(s, extra={"playlist_summary": self._playlist_summary(s.playlist_id)})
            for s in ch.schedules
            if s.active
        ]
        # annotate schedules with conflict kinds
        conflict_map: dict[str, set[str]] = {}
        for c in conflicts:
            for sid in c["schedule_ids"]:
                conflict_map.setdefault(sid, set()).add(c["kind"])
        for s in schedules:
            kinds = conflict_map.get(s["id"]) or set()
            if "AMBIGUOUS" in kinds:
                s["conflict_kind"] = "AMBIGUOUS"
                s["conflict_label"] = "Conflito de horário"
            elif "RESOLVED_BY_PRIORITY" in kinds:
                s["conflict_kind"] = "RESOLVED_BY_PRIORITY"
                s["conflict_label"] = "Prioridade define a exibição"
            else:
                s["conflict_kind"] = None
                s["conflict_label"] = None
            if current.get("schedule") and current["schedule"]["id"] == s["id"]:
                s["is_current"] = True
            else:
                s["is_current"] = False

        return {
            "channel": self.get_channel(channel_id),
            "at": when.isoformat(),
            "current": current,
            "next": nxt,
            "schedules": schedules,
            "conflicts": conflicts,
            "timezone_note": "Horários interpretados como relógio local do servidor (utcnow naive), mesma semântica do player.",
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

        items = (
            pl_svc.resolve_for_store(store_id, chosen_playlist)
            if chosen_playlist
            else pl_svc.resolve_for_store(store_id)
        )
        if items and meta["source"] == "none":
            meta["source"] = "store_default"
        return items, meta

    def _conflict_pairs(self, matching: list[Schedule]) -> list[dict[str, Any]]:
        """Conflito no instante = duas agendas com mesma prioridade ativas."""
        by_prio: dict[str, list[Schedule]] = {}
        for s in matching:
            by_prio.setdefault(s.priority, []).append(s)
        conflicts = []
        for prio, rows in by_prio.items():
            if len(rows) > 1:
                conflicts.append(
                    {
                        "kind": "AMBIGUOUS",
                        "priority": prio,
                        "schedule_ids": [r.id for r in rows],
                        "names": [r.name for r in rows],
                        "message": f"Conflito de horário — {len(rows)} agendas {PRIORITY_LABELS.get(prio, prio)} sobrepostas",
                    }
                )
        # also note resolved overlaps at instant
        if len(matching) > 1:
            weights = {s.id: PRIORITY_WEIGHT.get(s.priority, 10) for s in matching}
            max_w = max(weights.values())
            tops = [s for s in matching if weights[s.id] == max_w]
            lowers = [s for s in matching if weights[s.id] < max_w]
            if lowers and len(tops) == 1:
                conflicts.append(
                    {
                        "kind": "RESOLVED_BY_PRIORITY",
                        "priority": tops[0].priority,
                        "schedule_ids": [tops[0].id] + [s.id for s in lowers],
                        "names": [tops[0].name] + [s.name for s in lowers],
                        "message": f"Prioridade define a exibição ({PRIORITY_LABELS.get(tops[0].priority)})",
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

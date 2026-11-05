"""Analytics — KPIs operacionais derivados de tickets (UX-11 Analytics 2.0).

Semântica temporal: datetimes naive do servidor (utcnow), mesma regra do domínio.
Store timezone permanece débito arquitetural — não há segunda regra no React.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from statistics import mean, median
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.modules.devices.service import DeviceService
from app.modules.org.models.entities import Department
from app.modules.queue.models.entities import Queue, Ticket, utcnow
from app.modules.queue.models.enums import TicketStatus

# SLA de espera (hardcoded histórico — não lê QueuePriorityRule nesta sprint)
SLA_TARGET_WAIT = 600
SLA_WARNING_WAIT = 900


def _percentile(sorted_vals: list[float], p: float) -> float | None:
    """Percentil com interpolação linear sobre observações individuais ordenadas."""
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return float(sorted_vals[f])
    return float(sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f))


def _sec(start: datetime | None, end: datetime | None) -> int | None:
    """Duração em segundos. Missing timestamps → None (nunca 0 artificial)."""
    if not start or not end:
        return None
    return max(0, int((end - start).total_seconds()))


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min)
    end = start + timedelta(days=1)
    return start, end


def _stats(samples: list[float]) -> dict[str, float | None]:
    if not samples:
        return {
            "avg_seconds": None,
            "median_seconds": None,
            "p90_seconds": None,
            "max_seconds": None,
            "sample_count": 0,
        }
    sorted_vals = sorted(samples)
    return {
        "avg_seconds": round(mean(samples), 1),
        "median_seconds": round(median(samples), 1),
        "p90_seconds": round(_percentile(sorted_vals, 0.9), 1),
        "max_seconds": round(max(samples), 1),
        "sample_count": len(samples),
    }


def _wait_end(t: Ticket) -> datetime | None:
    return t.called_at or t.completed_at or t.no_show_at or t.cancelled_at


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def summary(
        self,
        *,
        day: date | None = None,
        queue_id: str | None = None,
        store_id: str | None = None,
    ) -> dict[str, Any]:
        """Compat Command Center / endpoint legado — cohort por issued_at no dia."""
        target = day or date.today()
        start, end = _day_bounds(target)
        queue_ids = self._resolve_queue_ids(store_id=store_id, queue_id=queue_id)
        tickets = self._tickets_issued_between(start, end, queue_ids=queue_ids)

        live_waiting = self._live_waiting(queue_ids=queue_ids, limit=30)

        by_status: dict[str, int] = {}
        by_type: dict[str, int] = {}
        wait_samples: list[float] = []
        service_samples: list[float] = []
        hourly_issued = [0] * 24
        hourly_completed = [0] * 24
        by_operator: dict[str, int] = {}
        sla = {"green": 0, "yellow": 0, "red": 0, "unknown": 0}

        for t in tickets:
            by_status[t.status] = by_status.get(t.status, 0) + 1
            by_type[t.ticket_type] = by_type.get(t.ticket_type, 0) + 1
            hourly_issued[t.issued_at.hour] += 1

            wait = _sec(t.issued_at, _wait_end(t))
            if wait is not None:
                wait_samples.append(float(wait))
                if wait < SLA_TARGET_WAIT:
                    sla["green"] += 1
                elif wait < SLA_WARNING_WAIT:
                    sla["yellow"] += 1
                else:
                    sla["red"] += 1
            else:
                sla["unknown"] += 1

            service = _sec(t.service_started_at, t.completed_at)
            if service is not None:
                service_samples.append(float(service))

            if t.status == TicketStatus.COMPLETED.value and t.completed_at:
                hourly_completed[t.completed_at.hour] += 1
                op = t.operator_id or "desconhecido"
                by_operator[op] = by_operator.get(op, 0) + 1

        wait_sorted = sorted(wait_samples)
        service_sorted = sorted(service_samples)
        issued = len(tickets)
        completed = by_status.get(TicketStatus.COMPLETED.value, 0)
        no_show = by_status.get(TicketStatus.NO_SHOW.value, 0)
        cancelled = by_status.get(TicketStatus.CANCELLED.value, 0)
        queue_name = None
        if queue_id:
            q = self.db.get(Queue, queue_id)
            queue_name = q.name if q else None

        def legacy_stats(vals: list[float], sorted_vals: list[float]) -> dict[str, float | None]:
            return {
                "avg_seconds": round(mean(vals), 1) if vals else None,
                "median_seconds": round(median(vals), 1) if vals else None,
                "p90_seconds": round(_percentile(sorted_vals, 0.9), 1) if sorted_vals else None,
                "max_seconds": round(max(vals), 1) if vals else None,
            }

        return {
            "date": target.isoformat(),
            "queue_id": queue_id,
            "store_id": store_id,
            "queue_name": queue_name,
            "kpis": {
                "issued": issued,
                "completed": completed,
                "waiting": len(live_waiting),
                "called": by_status.get(TicketStatus.CALLED.value, 0),
                "serving": by_status.get(TicketStatus.SERVING.value, 0),
                "no_show": no_show,
                "cancelled": cancelled,
                "abandon_rate": round((no_show + cancelled) / issued, 4) if issued else 0.0,
                "wait": legacy_stats(wait_samples, wait_sorted),
                "service": legacy_stats(service_samples, service_sorted),
            },
            "by_type": by_type,
            "by_status": by_status,
            "by_operator": [
                {"operator_id": oid, "completed": count}
                for oid, count in sorted(by_operator.items(), key=lambda x: -x[1])
            ],
            "hourly": [
                {"hour": h, "issued": hourly_issued[h], "completed": hourly_completed[h]}
                for h in range(24)
            ],
            "sla": {
                **sla,
                "target_wait_seconds": SLA_TARGET_WAIT,
                "warning_wait_seconds": SLA_WARNING_WAIT,
            },
            "current_waiting": [
                {
                    "id": t.id,
                    "number": t.display_number,
                    "type": t.ticket_type,
                    "status": t.status,
                    "issued_at": t.issued_at.isoformat(),
                    "wait_seconds": _sec(t.issued_at, utcnow()),
                }
                for t in live_waiting[:20]
            ],
        }

    def summary_for_store(self, *, store_id: str, day: date | None = None) -> dict[str, Any]:
        return self.summary(day=day, store_id=store_id)

    def overview(
        self,
        *,
        store_id: str,
        date_from: date,
        date_to: date,
        queue_id: str | None = None,
        ticket_type: str | None = None,
    ) -> dict[str, Any]:
        """UX-11 agregador read-only. Periodo inclusivo nas datas civis [from, to]."""
        if date_to < date_from:
            raise ValidationError("date_to deve ser >= date_from")
        start, _ = _day_bounds(date_from)
        _, end = _day_bounds(date_to)  # exclusive end = day after date_to 00:00

        all_store_queue_ids = self._resolve_queue_ids(store_id=store_id, queue_id=None) or []
        queue_ids = self._resolve_queue_ids(store_id=store_id, queue_id=queue_id)
        queues = self._queues_map(queue_ids)
        available_queues = [
            {"id": q.id, "name": q.name}
            for q in self._queues_map(all_store_queue_ids).values()
        ]

        issued_tickets = self._tickets_issued_between(start, end, queue_ids=queue_ids, ticket_type=ticket_type)
        completed_tickets = self._tickets_completed_between(start, end, queue_ids=queue_ids, ticket_type=ticket_type)
        no_show_tickets = self._tickets_by_ts(
            "no_show_at", start, end, queue_ids=queue_ids, ticket_type=ticket_type, status=TicketStatus.NO_SHOW.value
        )
        cancelled_tickets = self._tickets_by_ts(
            "cancelled_at", start, end, queue_ids=queue_ids, ticket_type=ticket_type
        )

        wait_samples: list[float] = []
        sla_green = sla_yellow = sla_red = sla_unknown = 0
        by_type: dict[str, int] = {}
        for t in issued_tickets:
            by_type[t.ticket_type] = by_type.get(t.ticket_type, 0) + 1
            wait = _sec(t.issued_at, _wait_end(t))
            if wait is None:
                sla_unknown += 1
                continue
            wait_samples.append(float(wait))
            if wait < SLA_TARGET_WAIT:
                sla_green += 1
            elif wait < SLA_WARNING_WAIT:
                sla_yellow += 1
            else:
                sla_red += 1

        service_samples: list[float] = []
        for t in completed_tickets:
            svc = _sec(t.service_started_at, t.completed_at)
            if svc is not None:
                service_samples.append(float(svc))

        evaluable = sla_green + sla_yellow + sla_red
        within = sla_green
        issued_n = len(issued_tickets)
        completed_n = len(completed_tickets)
        no_show_n = len(no_show_tickets)
        cancelled_n = len(cancelled_tickets)

        days = (date_to - date_from).days + 1
        granularity = "hour" if days <= 2 else "day"
        series = self._build_series(
            issued_tickets,
            completed_tickets,
            start=start,
            end=end,
            granularity=granularity,
        )
        demand_hourly = self._demand_hourly(issued_tickets)

        queues_cmp = self._queue_comparison(
            queues=queues,
            issued=issued_tickets,
            completed=completed_tickets,
            no_shows=no_show_tickets,
        )

        terminals = self._terminal_stats(completed_tickets)
        # operadores: só se houver IDs reais (não gamificar)
        operators = self._operator_stats(completed_tickets)

        devices_current = self._devices_current(store_id)

        # período anterior de mesma duração (opcional / baixo risco)
        prev_len = days
        prev_to = date_from - timedelta(days=1)
        prev_from = prev_to - timedelta(days=prev_len - 1)
        previous = self._period_snapshot(
            store_id=store_id,
            date_from=prev_from,
            date_to=prev_to,
            queue_id=queue_id,
            ticket_type=ticket_type,
        )

        wait_stats = _stats(wait_samples)
        service_stats = _stats(service_samples)
        duration_hours = max((end - start).total_seconds() / 3600.0, 1e-9)
        throughput_per_hour = round(completed_n / duration_hours, 2) if completed_n else 0.0

        return {
            "period": {
                "from": date_from.isoformat(),
                "to": date_to.isoformat(),
                "start": start.isoformat(),
                "end_exclusive": end.isoformat(),
                "days": days,
                "granularity": granularity,
                "timezone_note": "Horários naive do servidor (utcnow). Store timezone = débito.",
                "previous": {"from": prev_from.isoformat(), "to": prev_to.isoformat()},
            },
            "filters": {
                "store_id": store_id,
                "queue_id": queue_id,
                "ticket_type": ticket_type,
            },
            "cohorts": {
                "issued": "issued_at ∈ [from, to+1d)",
                "completed": "completed_at ∈ [from, to+1d)",
                "no_show": "no_show_at ∈ período e status=NO_SHOW (não inclui cancelled)",
                "cancelled": "cancelled_at ∈ período",
                "wait_sla": "tickets com issued_at ∈ período e wait_end avaliável",
                "service": "completed_at ∈ período com service_started_at e completed_at",
            },
            "metrics": {
                "issued": issued_n,
                "completed": completed_n,
                "no_show": no_show_n,
                "cancelled": cancelled_n,
                "completion_rate": round(completed_n / issued_n, 4) if issued_n else None,
                "completion_rate_note": "concluídas(cohort completed_at)/emitidas(cohort issued_at); tickets ainda abertos afetam o indicador em períodos em andamento.",
                "throughput_per_hour": throughput_per_hour,
                "wait": wait_stats,
                "service": service_stats,
                "sla": {
                    "green": sla_green,
                    "yellow": sla_yellow,
                    "red": sla_red,
                    "unknown": sla_unknown,
                    "evaluable": evaluable,
                    "within_target": within,
                    "within_target_rate": round(within / evaluable, 4) if evaluable else None,
                    "target_wait_seconds": SLA_TARGET_WAIT,
                    "warning_wait_seconds": SLA_WARNING_WAIT,
                    "definition": "Dentro do SLA = espera < 600s sobre tickets avaliáveis (wait_end presente). Unknown não conta como falha.",
                },
            },
            "comparison": self._compare_metrics(
                current={
                    "issued": issued_n,
                    "completed": completed_n,
                    "wait_avg": wait_stats["avg_seconds"],
                    "wait_p90": wait_stats["p90_seconds"],
                    "sla_rate": round(within / evaluable, 4) if evaluable else None,
                    "no_show": no_show_n,
                },
                previous=previous,
            ),
            "series": series,
            "demand_hourly": demand_hourly,
            "available_queues": available_queues,
            "queues": queues_cmp,
            "by_type": by_type,
            "terminals": terminals,
            "operators": operators,
            "devices_current": devices_current,
            "empty": issued_n == 0 and completed_n == 0 and no_show_n == 0,
        }

    # ── helpers ──────────────────────────────────────────────

    def _resolve_queue_ids(self, *, store_id: str | None, queue_id: str | None) -> list[str] | None:
        if queue_id:
            q = self.db.get(Queue, queue_id)
            if not q:
                return []
            if store_id:
                dept = self.db.get(Department, q.department_id)
                if not dept or dept.store_id != store_id:
                    return []  # isolation
            return [queue_id]
        if not store_id:
            return None
        dept_ids = list(self.db.scalars(select(Department.id).where(Department.store_id == store_id)).all())
        if not dept_ids:
            return []
        return list(self.db.scalars(select(Queue.id).where(Queue.department_id.in_(dept_ids))).all())

    def _queues_map(self, queue_ids: list[str] | None) -> dict[str, Queue]:
        if queue_ids is None:
            rows = list(self.db.scalars(select(Queue).order_by(Queue.name)).all())
        elif not queue_ids:
            return {}
        else:
            rows = list(self.db.scalars(select(Queue).where(Queue.id.in_(queue_ids)).order_by(Queue.name)).all())
        return {q.id: q for q in rows}

    def _tickets_issued_between(
        self,
        start: datetime,
        end: datetime,
        *,
        queue_ids: list[str] | None,
        ticket_type: str | None = None,
    ) -> list[Ticket]:
        filters = [Ticket.issued_at >= start, Ticket.issued_at < end]
        if queue_ids is not None:
            if not queue_ids:
                return []
            filters.append(Ticket.queue_id.in_(queue_ids))
        if ticket_type:
            filters.append(Ticket.ticket_type == ticket_type)
        return list(self.db.scalars(select(Ticket).where(*filters)).all())

    def _tickets_completed_between(
        self,
        start: datetime,
        end: datetime,
        *,
        queue_ids: list[str] | None,
        ticket_type: str | None = None,
    ) -> list[Ticket]:
        filters = [
            Ticket.completed_at.is_not(None),
            Ticket.completed_at >= start,
            Ticket.completed_at < end,
            Ticket.status == TicketStatus.COMPLETED.value,
        ]
        if queue_ids is not None:
            if not queue_ids:
                return []
            filters.append(Ticket.queue_id.in_(queue_ids))
        if ticket_type:
            filters.append(Ticket.ticket_type == ticket_type)
        return list(self.db.scalars(select(Ticket).where(*filters)).all())

    def _tickets_by_ts(
        self,
        field: str,
        start: datetime,
        end: datetime,
        *,
        queue_ids: list[str] | None,
        ticket_type: str | None = None,
        status: str | None = None,
    ) -> list[Ticket]:
        col = getattr(Ticket, field)
        filters = [col.is_not(None), col >= start, col < end]
        if status:
            filters.append(Ticket.status == status)
        if queue_ids is not None:
            if not queue_ids:
                return []
            filters.append(Ticket.queue_id.in_(queue_ids))
        if ticket_type:
            filters.append(Ticket.ticket_type == ticket_type)
        return list(self.db.scalars(select(Ticket).where(*filters)).all())

    def _live_waiting(self, *, queue_ids: list[str] | None, limit: int = 30) -> list[Ticket]:
        q = select(Ticket).where(Ticket.status == TicketStatus.WAITING.value)
        if queue_ids is not None:
            if not queue_ids:
                return []
            q = q.where(Ticket.queue_id.in_(queue_ids))
        return list(self.db.scalars(q.order_by(Ticket.issued_at.asc()).limit(limit)).all())

    def _build_series(
        self,
        issued: list[Ticket],
        completed: list[Ticket],
        *,
        start: datetime,
        end: datetime,
        granularity: str,
    ) -> dict[str, Any]:
        if granularity == "hour":
            buckets: dict[str, dict[str, int]] = {}
            cursor = start
            while cursor < end:
                key = cursor.strftime("%Y-%m-%dT%H:00")
                buckets[key] = {"issued": 0, "completed": 0}
                cursor += timedelta(hours=1)
            for t in issued:
                key = t.issued_at.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:00")
                if key in buckets:
                    buckets[key]["issued"] += 1
            for t in completed:
                if not t.completed_at:
                    continue
                key = t.completed_at.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:00")
                if key in buckets:
                    buckets[key]["completed"] += 1
            points = [{"bucket": k, **v} for k, v in buckets.items()]
        else:
            buckets = {}
            cursor_d = start.date()
            end_d = (end - timedelta(seconds=1)).date()
            while cursor_d <= end_d:
                key = cursor_d.isoformat()
                buckets[key] = {"issued": 0, "completed": 0}
                cursor_d += timedelta(days=1)
            for t in issued:
                key = t.issued_at.date().isoformat()
                if key in buckets:
                    buckets[key]["issued"] += 1
            for t in completed:
                if not t.completed_at:
                    continue
                key = t.completed_at.date().isoformat()
                if key in buckets:
                    buckets[key]["completed"] += 1
            points = [{"bucket": k, **v} for k, v in buckets.items()]

        # wait/p90 por bucket (observações individuais do bucket de emissão)
        wait_by_bucket: dict[str, list[float]] = {p["bucket"]: [] for p in points}
        for t in issued:
            if granularity == "hour":
                key = t.issued_at.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:00")
            else:
                key = t.issued_at.date().isoformat()
            w = _sec(t.issued_at, _wait_end(t))
            if w is not None and key in wait_by_bucket:
                wait_by_bucket[key].append(float(w))
        wait_points = []
        for p in points:
            st = _stats(wait_by_bucket.get(p["bucket"], []))
            wait_points.append(
                {
                    "bucket": p["bucket"],
                    "avg_seconds": st["avg_seconds"],
                    "p90_seconds": st["p90_seconds"],
                    "sample_count": st["sample_count"],
                }
            )
        return {
            "granularity": granularity,
            "volume": points,
            "wait": wait_points,
        }

    def _demand_hourly(self, issued: list[Ticket]) -> list[dict[str, Any]]:
        hours = [0] * 24
        for t in issued:
            hours[t.issued_at.hour] += 1
        return [{"hour": h, "issued": hours[h]} for h in range(24)]

    def _queue_comparison(
        self,
        *,
        queues: dict[str, Queue],
        issued: list[Ticket],
        completed: list[Ticket],
        no_shows: list[Ticket],
    ) -> list[dict[str, Any]]:
        by_q_issued: dict[str, list[Ticket]] = {qid: [] for qid in queues}
        by_q_completed: dict[str, list[Ticket]] = {qid: [] for qid in queues}
        by_q_noshow: dict[str, int] = {qid: 0 for qid in queues}
        for t in issued:
            by_q_issued.setdefault(t.queue_id, []).append(t)
        for t in completed:
            by_q_completed.setdefault(t.queue_id, []).append(t)
        for t in no_shows:
            by_q_noshow[t.queue_id] = by_q_noshow.get(t.queue_id, 0) + 1

        rows = []
        for qid, q in queues.items():
            issued_list = by_q_issued.get(qid, [])
            completed_list = by_q_completed.get(qid, [])
            waits: list[float] = []
            g = y = r = u = 0
            for t in issued_list:
                w = _sec(t.issued_at, _wait_end(t))
                if w is None:
                    u += 1
                    continue
                waits.append(float(w))
                if w < SLA_TARGET_WAIT:
                    g += 1
                elif w < SLA_WARNING_WAIT:
                    y += 1
                else:
                    r += 1
            evaluable = g + y + r
            st = _stats(waits)
            rows.append(
                {
                    "queue_id": qid,
                    "name": q.name,
                    "issued": len(issued_list),
                    "completed": len(completed_list),
                    "no_show": by_q_noshow.get(qid, 0),
                    "wait_avg_seconds": st["avg_seconds"],
                    "wait_p90_seconds": st["p90_seconds"],
                    "wait_sample_count": st["sample_count"],
                    "sla_within_rate": round(g / evaluable, 4) if evaluable else None,
                    "sla_evaluable": evaluable,
                    "sla_green": g,
                    "sla_yellow": y,
                    "sla_red": r,
                    "sla_unknown": u,
                }
            )
        # default order: pior SLA, depois maior P90
        def sort_key(row: dict[str, Any]) -> tuple:
            rate = row["sla_within_rate"]
            p90 = row["wait_p90_seconds"]
            return (
                0 if rate is None else 1,
                rate if rate is not None else 1.0,
                -(p90 or 0),
                -row["issued"],
            )

        rows.sort(key=sort_key)
        return rows

    def _terminal_stats(self, completed: list[Ticket]) -> dict[str, Any]:
        has_any = any(t.terminal_id for t in completed)
        if not has_any:
            return {
                "available": False,
                "reason": "Nenhum terminal_id histórico nos atendimentos concluídos do período.",
                "items": [],
            }
        buckets: dict[str, dict[str, Any]] = {}
        for t in completed:
            tid = t.terminal_id or "sem_balcão"
            b = buckets.setdefault(tid, {"terminal_id": tid, "completed": 0, "service_samples": []})
            b["completed"] += 1
            svc = _sec(t.service_started_at, t.completed_at)
            if svc is not None:
                b["service_samples"].append(float(svc))
        items = []
        for b in buckets.values():
            st = _stats(b["service_samples"])
            items.append(
                {
                    "terminal_id": b["terminal_id"],
                    "completed": b["completed"],
                    "service_avg_seconds": st["avg_seconds"],
                    "service_sample_count": st["sample_count"],
                }
            )
        items.sort(key=lambda x: -x["completed"])
        return {
            "available": True,
            "note": "Desempenho por balcão (terminal_id no ticket). Sem ranking gamificado.",
            "items": items,
        }

    def _operator_stats(self, completed: list[Ticket]) -> dict[str, Any]:
        known = [t for t in completed if t.operator_id]
        if not known:
            return {
                "available": False,
                "reason": "Sem operator_id histórico confiável no período.",
                "items": [],
            }
        buckets: dict[str, int] = {}
        for t in known:
            buckets[t.operator_id] = buckets.get(t.operator_id, 0) + 1  # type: ignore[arg-type]
        items = [
            {"operator_id": oid, "completed": count}
            for oid, count in sorted(buckets.items(), key=lambda x: -x[1])
        ]
        return {
            "available": True,
            "note": "Contagem por operator_id persistido no atendimento. Sem ranking/gamificação.",
            "items": items,
        }

    def _devices_current(self, store_id: str) -> dict[str, Any]:
        try:
            devices = DeviceService(self.db).list_devices(store_id=store_id)
        except Exception:
            return {
                "available": False,
                "label": "Situação atual da frota",
                "error": True,
                "note": "Snapshot atual via DeviceService._compute_status — não é uptime histórico.",
            }
        counts = {"ONLINE": 0, "DEGRADED": 0, "OFFLINE": 0, "DISABLED": 0}
        for d in devices:
            st = d.get("status") or "OFFLINE"
            if st in counts:
                counts[st] += 1
            else:
                counts["OFFLINE"] += 1
        return {
            "available": True,
            "label": "Situação atual da frota",
            "note": "Snapshot agora (DeviceService._compute_status). Não é disponibilidade histórica do período.",
            "total": len(devices),
            "online": counts["ONLINE"],
            "degraded": counts["DEGRADED"],
            "offline": counts["OFFLINE"],
            "disabled": counts["DISABLED"],
        }

    def _period_snapshot(
        self,
        *,
        store_id: str,
        date_from: date,
        date_to: date,
        queue_id: str | None,
        ticket_type: str | None,
    ) -> dict[str, Any]:
        start, _ = _day_bounds(date_from)
        _, end = _day_bounds(date_to)
        queue_ids = self._resolve_queue_ids(store_id=store_id, queue_id=queue_id)
        issued = self._tickets_issued_between(start, end, queue_ids=queue_ids, ticket_type=ticket_type)
        completed = self._tickets_completed_between(start, end, queue_ids=queue_ids, ticket_type=ticket_type)
        no_shows = self._tickets_by_ts(
            "no_show_at", start, end, queue_ids=queue_ids, ticket_type=ticket_type, status=TicketStatus.NO_SHOW.value
        )
        waits: list[float] = []
        g = y = r = 0
        for t in issued:
            w = _sec(t.issued_at, _wait_end(t))
            if w is None:
                continue
            waits.append(float(w))
            if w < SLA_TARGET_WAIT:
                g += 1
            elif w < SLA_WARNING_WAIT:
                y += 1
            else:
                r += 1
        evaluable = g + y + r
        st = _stats(waits)
        return {
            "issued": len(issued),
            "completed": len(completed),
            "no_show": len(no_shows),
            "wait_avg": st["avg_seconds"],
            "wait_p90": st["p90_seconds"],
            "sla_rate": round(g / evaluable, 4) if evaluable else None,
        }

    def _compare_metrics(self, *, current: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
        def delta(cur: float | None, prev: float | None) -> dict[str, Any] | None:
            if cur is None or prev is None:
                return None
            if prev == 0:
                return {"absolute": round(cur - prev, 4), "pct": None}
            return {
                "absolute": round(cur - prev, 4),
                "pct": round((cur - prev) / abs(prev), 4),
            }

        return {
            "previous": previous,
            "issued": delta(float(current["issued"]), float(previous["issued"])),
            "completed": delta(float(current["completed"]), float(previous["completed"])),
            "wait_avg": delta(current["wait_avg"], previous["wait_avg"]),
            "wait_p90": delta(current["wait_p90"], previous["wait_p90"]),
            "sla_rate": delta(current["sla_rate"], previous["sla_rate"]),
            "no_show": delta(float(current["no_show"]), float(previous["no_show"])),
            "note": "Período anterior = mesma duração imediatamente anterior. Não é weekday-aligned.",
        }

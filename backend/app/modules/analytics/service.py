"""Analytics MVP — KPIs operacionais derivados de tickets do dia."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from statistics import mean, median
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.queue.models.entities import Queue, Ticket, utcnow
from app.modules.queue.models.enums import TicketStatus


def _percentile(sorted_vals: list[float], p: float) -> float | None:
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
    if not start or not end:
        return None
    return max(0, int((end - start).total_seconds()))


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min)
    end = start + timedelta(days=1)
    return start, end


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def summary(
        self,
        *,
        day: date | None = None,
        queue_id: str | None = None,
    ) -> dict[str, Any]:
        target = day or date.today()
        start, end = _day_bounds(target)

        filters = [Ticket.issued_at >= start, Ticket.issued_at < end]
        queue_name = None
        if queue_id:
            filters.append(Ticket.queue_id == queue_id)
            q = self.db.get(Queue, queue_id)
            queue_name = q.name if q else None

        tickets = list(self.db.scalars(select(Ticket).where(*filters).order_by(Ticket.issued_at.asc())).all())

        # Aguardando ao vivo (não só do dia)
        live_waiting_q = select(Ticket).where(Ticket.status == TicketStatus.WAITING.value)
        if queue_id:
            live_waiting_q = live_waiting_q.where(Ticket.queue_id == queue_id)
        live_waiting = list(self.db.scalars(live_waiting_q.order_by(Ticket.issued_at.asc()).limit(30)).all())

        issued = len(tickets)
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

            wait_end = t.called_at or t.completed_at or t.no_show_at or t.cancelled_at
            wait = _sec(t.issued_at, wait_end)
            if wait is not None:
                wait_samples.append(float(wait))
                if wait < 600:
                    sla["green"] += 1
                elif wait < 900:
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

        def stats(vals: list[float], sorted_vals: list[float]) -> dict[str, float | None]:
            return {
                "avg_seconds": round(mean(vals), 1) if vals else None,
                "median_seconds": round(median(vals), 1) if vals else None,
                "p90_seconds": round(_percentile(sorted_vals, 0.9), 1) if sorted_vals else None,
                "max_seconds": round(max(vals), 1) if vals else None,
            }

        completed = by_status.get(TicketStatus.COMPLETED.value, 0)
        no_show = by_status.get(TicketStatus.NO_SHOW.value, 0)
        cancelled = by_status.get(TicketStatus.CANCELLED.value, 0)

        return {
            "date": target.isoformat(),
            "queue_id": queue_id,
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
                "wait": stats(wait_samples, wait_sorted),
                "service": stats(service_samples, service_sorted),
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
                "target_wait_seconds": 600,
                "warning_wait_seconds": 900,
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

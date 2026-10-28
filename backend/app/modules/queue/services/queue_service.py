from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.queue.models.entities import (
    IdempotencyRecord,
    Queue,
    QueuePriorityRule,
    QueueSequence,
    Ticket,
    TicketEvent,
)
from app.modules.queue.models.enums import (
    TicketEventType,
    TicketSource,
    TicketStatus,
    TicketType,
)
from app.modules.queue.policies.selection import (
    PriorityRules,
    QueueSelectionEngine,
    TicketCandidate,
)
from app.modules.queue.services.state_machine import ensure_transition


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class QueueService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ helpers
    def get_queue(self, queue_id: str) -> Queue:
        queue = self.db.get(Queue, queue_id)
        if not queue:
            raise NotFoundError("Fila não encontrada")
        return queue

    def get_ticket(self, ticket_id: str) -> Ticket:
        ticket = self.db.get(Ticket, ticket_id)
        if not ticket:
            raise NotFoundError("Senha não encontrada")
        return ticket

    def _period_key(self, queue: Queue, when: datetime | None = None) -> str:
        ref = when or utcnow()
        if queue.reset_policy == "DAILY":
            return ref.date().isoformat()
        if queue.reset_policy == "NEVER":
            return "never"
        if queue.reset_policy == "SHIFT":
            # MVP: manhã/tarde por data
            shift = "AM" if ref.hour < 14 else "PM"
            return f"{ref.date().isoformat()}-{shift}"
        return "manual"

    def _prefix_for(self, queue: Queue, ticket_type: str) -> str:
        if ticket_type in (TicketType.PRIORITY.value, TicketType.PRIORITY_PLUS.value):
            return queue.priority_prefix
        return queue.normal_prefix

    def _format_display(self, queue: Queue, ticket_type: str, number: int) -> str:
        return f"{self._prefix_for(queue, ticket_type)}{number:0{queue.digits}d}"

    def _rules_for(self, queue: Queue) -> PriorityRules:
        rule = queue.priority_rule
        if rule and rule.active:
            return PriorityRules(
                normal_weight=rule.normal_weight,
                priority_weight=rule.priority_weight,
                priority_max_wait_seconds=rule.priority_max_wait_seconds,
                normal_max_wait_seconds=rule.normal_max_wait_seconds,
            )
        return PriorityRules()

    def _add_event(
        self,
        ticket: Ticket,
        event_type: str,
        *,
        operator_id: str | None = None,
        terminal_id: str | None = None,
        metadata: dict | None = None,
    ) -> TicketEvent:
        event = TicketEvent(
            ticket_id=ticket.id,
            event_type=event_type,
            event_at=utcnow(),
            operator_id=operator_id,
            terminal_id=terminal_id,
            metadata_json=metadata,
        )
        self.db.add(event)
        return event

    def _get_idempotency(self, scope: str, key: str | None) -> dict | None:
        if not key:
            return None
        row = self.db.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.scope == scope,
                IdempotencyRecord.key == key,
            )
        )
        return row.response_json if row else None

    def _save_idempotency(self, scope: str, key: str | None, response: dict) -> None:
        if not key:
            return
        self.db.add(IdempotencyRecord(scope=scope, key=key, response_json=response))

    def _next_sequence_number(self, queue: Queue, ticket_type: str, period_key: str) -> int:
        stmt: Select[tuple[QueueSequence]] = (
            select(QueueSequence)
            .where(
                QueueSequence.queue_id == queue.id,
                QueueSequence.ticket_type == ticket_type,
                QueueSequence.period_key == period_key,
            )
            .with_for_update()
        )
        seq = self.db.scalar(stmt)
        if seq is None:
            # Corrida na criação da linha: savepoint + retry
            try:
                with self.db.begin_nested():
                    self.db.add(
                        QueueSequence(
                            queue_id=queue.id,
                            ticket_type=ticket_type,
                            period_key=period_key,
                            current_number=queue.initial_number - 1,
                        )
                    )
                    self.db.flush()
            except IntegrityError:
                pass
            seq = self.db.scalar(stmt)
            if seq is None:
                raise ConflictError("Não foi possível obter sequência da fila")

        next_number = seq.current_number + 1
        if next_number > queue.final_number:
            raise ConflictError("Sequência de senhas esgotada para o período")
        if next_number < queue.initial_number:
            next_number = queue.initial_number

        seq.current_number = next_number
        self.db.flush()
        return next_number

    def _waiting_candidates(self, queue_id: str) -> list[TicketCandidate]:
        rows = self.db.scalars(
            select(Ticket)
            .where(Ticket.queue_id == queue_id, Ticket.status == TicketStatus.WAITING.value)
            .order_by(Ticket.issued_at.asc())
        ).all()
        return [
            TicketCandidate(
                id=t.id,
                ticket_type=t.ticket_type,
                issued_at=t.issued_at,
                display_number=t.display_number,
            )
            for t in rows
        ]

    def _recent_call_types(self, queue_id: str, limit: int = 20) -> list[str]:
        rows = self.db.scalars(
            select(Ticket)
            .where(
                Ticket.queue_id == queue_id,
                Ticket.called_at.is_not(None),
            )
            .order_by(Ticket.called_at.desc())
            .limit(limit)
        ).all()
        # ordem cronológica
        return [t.ticket_type for t in reversed(rows)]

    def _avg_service_seconds(self, queue_id: str) -> float:
        rows = self.db.scalars(
            select(Ticket)
            .where(
                Ticket.queue_id == queue_id,
                Ticket.status == TicketStatus.COMPLETED.value,
                Ticket.service_started_at.is_not(None),
                Ticket.completed_at.is_not(None),
            )
            .order_by(Ticket.completed_at.desc())
            .limit(50)
        ).all()
        if not rows:
            return 180.0
        total = 0.0
        for t in rows:
            assert t.service_started_at and t.completed_at
            total += (t.completed_at - t.service_started_at).total_seconds()
        return max(60.0, total / len(rows))

    def _people_ahead(self, queue: Queue, ticket: Ticket) -> int:
        waiting = self._waiting_candidates(queue.id)
        ahead = 0
        for c in waiting:
            if c.id == ticket.id:
                break
            ahead += 1
        else:
            # ticket acabou de ser criado e está no fim
            ahead = len(waiting) - 1 if waiting else 0
            if ahead < 0:
                ahead = 0
        return max(0, ahead)

    def estimate_wait_seconds(self, queue: Queue, people_ahead: int) -> int:
        avg = self._avg_service_seconds(queue.id)
        active_operators = 1  # MVP
        return int((people_ahead * avg) / max(1, active_operators))

    def ticket_to_dict(self, ticket: Ticket, *, people_ahead: int | None = None, estimated_wait: int | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": ticket.id,
            "queue_id": ticket.queue_id,
            "number": ticket.display_number,
            "sequence_number": ticket.sequence_number,
            "type": ticket.ticket_type,
            "status": ticket.status,
            "issued_at": ticket.issued_at.isoformat() if ticket.issued_at else None,
            "called_at": ticket.called_at.isoformat() if ticket.called_at else None,
            "service_started_at": ticket.service_started_at.isoformat() if ticket.service_started_at else None,
            "completed_at": ticket.completed_at.isoformat() if ticket.completed_at else None,
            "cancelled_at": ticket.cancelled_at.isoformat() if ticket.cancelled_at else None,
            "no_show_at": ticket.no_show_at.isoformat() if ticket.no_show_at else None,
            "terminal_id": ticket.terminal_id,
            "operator_id": ticket.operator_id,
            "source": ticket.source,
        }
        if people_ahead is not None:
            payload["people_ahead"] = people_ahead
        if estimated_wait is not None:
            payload["estimated_wait_seconds"] = estimated_wait
        return payload

    # ------------------------------------------------------------------ CRUD fila
    def create_queue(
        self,
        *,
        department_id: str,
        name: str,
        normal_prefix: str = "A",
        priority_prefix: str = "P",
        digits: int = 3,
        initial_number: int = 1,
        final_number: int = 999,
        reset_policy: str = "DAILY",
        priority_strategy: str = "WEIGHTED",
        normal_weight: int = 3,
        priority_weight: int = 1,
        priority_max_wait_seconds: int = 600,
        normal_max_wait_seconds: int | None = None,
    ) -> Queue:
        queue = Queue(
            department_id=department_id,
            name=name,
            normal_prefix=normal_prefix,
            priority_prefix=priority_prefix,
            digits=digits,
            initial_number=initial_number,
            final_number=final_number,
            reset_policy=reset_policy,
            priority_strategy=priority_strategy,
        )
        self.db.add(queue)
        self.db.flush()
        rule = QueuePriorityRule(
            queue_id=queue.id,
            normal_weight=normal_weight,
            priority_weight=priority_weight,
            priority_max_wait_seconds=priority_max_wait_seconds,
            normal_max_wait_seconds=normal_max_wait_seconds,
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(queue)
        return queue

    def list_queues(self) -> list[Queue]:
        return list(
            self.db.scalars(select(Queue).options(joinedload(Queue.priority_rule)).order_by(Queue.name)).all()
        )

    def update_queue(self, queue_id: str, **fields: Any) -> Queue:
        queue = self.get_queue(queue_id)
        rule_fields = {
            "normal_weight",
            "priority_weight",
            "priority_max_wait_seconds",
            "normal_max_wait_seconds",
        }
        for key, value in fields.items():
            if value is None:
                continue
            if key in rule_fields:
                if not queue.priority_rule:
                    queue.priority_rule = QueuePriorityRule(queue_id=queue.id)
                setattr(queue.priority_rule, key, value)
            elif hasattr(queue, key):
                setattr(queue, key, value)
        self.db.commit()
        self.db.refresh(queue)
        return queue

    # ------------------------------------------------------------------ emissão
    def create_ticket(
        self,
        queue_id: str,
        *,
        ticket_type: str = TicketType.NORMAL.value,
        source: str = TicketSource.KIOSK.value,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        scope = f"create_ticket:{queue_id}"
        cached = self._get_idempotency(scope, idempotency_key)
        if cached:
            return cached

        if ticket_type not in {t.value for t in TicketType}:
            raise ConflictError("Tipo de senha inválido")

        queue = self.get_queue(queue_id)
        if queue.status != "OPEN":
            raise ConflictError("Fila não está aberta")

        period_key = self._period_key(queue)
        number = self._next_sequence_number(queue, ticket_type, period_key)
        display = self._format_display(queue, ticket_type, number)

        ticket = Ticket(
            queue_id=queue.id,
            sequence_number=number,
            display_number=display,
            period_key=period_key,
            ticket_type=ticket_type,
            status=TicketStatus.WAITING.value,
            issued_at=utcnow(),
            source=source,
        )
        self.db.add(ticket)
        self.db.flush()
        self._add_event(ticket, TicketEventType.TICKET_CREATED.value, metadata={"number": display})

        people_ahead = self._people_ahead(queue, ticket)
        estimated = self.estimate_wait_seconds(queue, people_ahead)
        payload = self.ticket_to_dict(ticket, people_ahead=people_ahead, estimated_wait=estimated)
        self._save_idempotency(scope, idempotency_key, payload)
        self.db.commit()
        return payload

    # ------------------------------------------------------------------ operação
    def call_next(
        self,
        queue_id: str,
        *,
        terminal_id: str | None = None,
        operator_id: str | None = None,
        idempotency_key: str | None = None,
        auto_complete_current: bool = True,
        auto_start: bool = False,
    ) -> dict[str, Any]:
        scope = f"call_next:{queue_id}:{terminal_id or 'none'}"
        cached = self._get_idempotency(scope, idempotency_key)
        if cached:
            return cached

        # Lock da fila inteira: dois terminais não chamam a mesma senha
        queue = self.db.scalar(select(Queue).where(Queue.id == queue_id).with_for_update())
        if not queue:
            raise NotFoundError("Fila não encontrada")

        if auto_complete_current and terminal_id:
            current = self.db.scalar(
                select(Ticket)
                .where(
                    Ticket.queue_id == queue_id,
                    Ticket.terminal_id == terminal_id,
                    Ticket.status.in_([TicketStatus.CALLED.value, TicketStatus.SERVING.value]),
                )
                .with_for_update()
            )
            if current:
                if current.status == TicketStatus.CALLED.value:
                    ensure_transition(current.status, TicketStatus.SERVING.value)
                    current.status = TicketStatus.SERVING.value
                    current.service_started_at = utcnow()
                    self._add_event(
                        current,
                        TicketEventType.SERVICE_STARTED.value,
                        operator_id=operator_id,
                        terminal_id=terminal_id,
                    )
                ensure_transition(current.status, TicketStatus.COMPLETED.value)
                current.status = TicketStatus.COMPLETED.value
                current.completed_at = utcnow()
                self._add_event(
                    current,
                    TicketEventType.SERVICE_COMPLETED.value,
                    operator_id=operator_id,
                    terminal_id=terminal_id,
                )

        candidates = self._waiting_candidates(queue_id)
        if not candidates:
            raise NotFoundError("Não há senhas aguardando")

        # Lock tickets waiting to avoid double call
        waiting_rows = list(
            self.db.scalars(
                select(Ticket)
                .where(Ticket.queue_id == queue_id, Ticket.status == TicketStatus.WAITING.value)
                .order_by(Ticket.issued_at.asc())
                .with_for_update()
            ).all()
        )
        locked_candidates = [
            TicketCandidate(
                id=t.id,
                ticket_type=t.ticket_type,
                issued_at=t.issued_at,
                display_number=t.display_number,
            )
            for t in waiting_rows
        ]

        engine = QueueSelectionEngine(queue.priority_strategy)
        chosen = engine.select_next(
            locked_candidates,
            self._rules_for(queue),
            recent_call_types=self._recent_call_types(queue_id),
        )
        if not chosen:
            raise NotFoundError("Não há senhas aguardando")

        ticket = next(t for t in waiting_rows if t.id == chosen.id)
        ensure_transition(ticket.status, TicketStatus.CALLED.value)
        ticket.status = TicketStatus.CALLED.value
        ticket.called_at = utcnow()
        ticket.terminal_id = terminal_id
        ticket.operator_id = operator_id
        self._add_event(
            ticket,
            TicketEventType.TICKET_CALLED.value,
            operator_id=operator_id,
            terminal_id=terminal_id,
        )

        if auto_start:
            ensure_transition(ticket.status, TicketStatus.SERVING.value)
            ticket.status = TicketStatus.SERVING.value
            ticket.service_started_at = utcnow()
            self._add_event(
                ticket,
                TicketEventType.SERVICE_STARTED.value,
                operator_id=operator_id,
                terminal_id=terminal_id,
            )

        payload = self.ticket_to_dict(ticket)
        self._save_idempotency(scope, idempotency_key, payload)
        self.db.commit()
        return payload

    def recall(self, ticket_id: str, *, operator_id: str | None = None, terminal_id: str | None = None) -> dict[str, Any]:
        ticket = self.get_ticket(ticket_id)
        if ticket.status not in {TicketStatus.CALLED.value, TicketStatus.SERVING.value}:
            raise ConflictError("Somente senhas chamadas ou em atendimento podem ser rechamadas")
        self._add_event(
            ticket,
            TicketEventType.TICKET_RECALLED.value,
            operator_id=operator_id,
            terminal_id=terminal_id or ticket.terminal_id,
        )
        self.db.commit()
        self.db.refresh(ticket)
        return self.ticket_to_dict(ticket)

    def start(self, ticket_id: str, *, operator_id: str | None = None, terminal_id: str | None = None) -> dict[str, Any]:
        ticket = self.get_ticket(ticket_id)
        ensure_transition(ticket.status, TicketStatus.SERVING.value)
        ticket.status = TicketStatus.SERVING.value
        ticket.service_started_at = utcnow()
        if operator_id:
            ticket.operator_id = operator_id
        if terminal_id:
            ticket.terminal_id = terminal_id
        self._add_event(
            ticket,
            TicketEventType.SERVICE_STARTED.value,
            operator_id=operator_id,
            terminal_id=terminal_id,
        )
        self.db.commit()
        self.db.refresh(ticket)
        return self.ticket_to_dict(ticket)

    def complete(self, ticket_id: str, *, operator_id: str | None = None, terminal_id: str | None = None) -> dict[str, Any]:
        ticket = self.get_ticket(ticket_id)
        if ticket.status == TicketStatus.CALLED.value:
            # atalho: CALLED → SERVING → COMPLETED
            ensure_transition(ticket.status, TicketStatus.SERVING.value)
            ticket.status = TicketStatus.SERVING.value
            ticket.service_started_at = ticket.service_started_at or utcnow()
            self._add_event(
                ticket,
                TicketEventType.SERVICE_STARTED.value,
                operator_id=operator_id,
                terminal_id=terminal_id,
            )
        ensure_transition(ticket.status, TicketStatus.COMPLETED.value)
        ticket.status = TicketStatus.COMPLETED.value
        ticket.completed_at = utcnow()
        self._add_event(
            ticket,
            TicketEventType.SERVICE_COMPLETED.value,
            operator_id=operator_id,
            terminal_id=terminal_id,
        )
        self.db.commit()
        self.db.refresh(ticket)
        return self.ticket_to_dict(ticket)

    def no_show(self, ticket_id: str, *, operator_id: str | None = None, terminal_id: str | None = None) -> dict[str, Any]:
        ticket = self.get_ticket(ticket_id)
        ensure_transition(ticket.status, TicketStatus.NO_SHOW.value)
        ticket.status = TicketStatus.NO_SHOW.value
        ticket.no_show_at = utcnow()
        self._add_event(
            ticket,
            TicketEventType.TICKET_NO_SHOW.value,
            operator_id=operator_id,
            terminal_id=terminal_id,
        )
        self.db.commit()
        self.db.refresh(ticket)
        return self.ticket_to_dict(ticket)

    def cancel(self, ticket_id: str, *, operator_id: str | None = None) -> dict[str, Any]:
        ticket = self.get_ticket(ticket_id)
        ensure_transition(ticket.status, TicketStatus.CANCELLED.value)
        ticket.status = TicketStatus.CANCELLED.value
        ticket.cancelled_at = utcnow()
        self._add_event(ticket, TicketEventType.TICKET_CANCELLED.value, operator_id=operator_id)
        self.db.commit()
        self.db.refresh(ticket)
        return self.ticket_to_dict(ticket)

    # ------------------------------------------------------------------ consultas
    def waiting_list(self, queue_id: str) -> list[dict[str, Any]]:
        self.get_queue(queue_id)
        rows = self.db.scalars(
            select(Ticket)
            .where(Ticket.queue_id == queue_id, Ticket.status == TicketStatus.WAITING.value)
            .order_by(Ticket.issued_at.asc())
        ).all()
        return [self.ticket_to_dict(t) for t in rows]

    def queue_status(self, queue_id: str) -> dict[str, Any]:
        queue = self.get_queue(queue_id)
        waiting = self.waiting_list(queue_id)
        current = self.db.scalar(
            select(Ticket)
            .where(
                Ticket.queue_id == queue_id,
                Ticket.status.in_([TicketStatus.CALLED.value, TicketStatus.SERVING.value]),
            )
            .order_by(Ticket.called_at.desc())
            .limit(1)
        )
        last_called = self.db.scalars(
            select(Ticket)
            .where(Ticket.queue_id == queue_id, Ticket.called_at.is_not(None))
            .order_by(Ticket.called_at.desc())
            .limit(5)
        ).all()
        priority_waiting = sum(1 for t in waiting if t["type"] in {"PRIORITY", "PRIORITY_PLUS"})
        return {
            "queue_id": queue.id,
            "department_id": queue.department_id,
            "name": queue.name,
            "status": queue.status,
            "waiting_count": len(waiting),
            "priority_waiting": priority_waiting,
            "estimated_wait_seconds": self.estimate_wait_seconds(queue, len(waiting)),
            "current": self.ticket_to_dict(current) if current else None,
            "last_called": [self.ticket_to_dict(t) for t in last_called],
            "priority_strategy": queue.priority_strategy,
            "priority_rule": {
                "normal_weight": queue.priority_rule.normal_weight if queue.priority_rule else 3,
                "priority_weight": queue.priority_rule.priority_weight if queue.priority_rule else 1,
                "priority_max_wait_seconds": queue.priority_rule.priority_max_wait_seconds if queue.priority_rule else 600,
                "normal_max_wait_seconds": queue.priority_rule.normal_max_wait_seconds if queue.priority_rule else None,
            },
        }

    def operator_panel(self, queue_id: str, terminal_id: str | None = None) -> dict[str, Any]:
        status = self.queue_status(queue_id)
        current = None
        if terminal_id:
            current = self.db.scalar(
                select(Ticket)
                .where(
                    Ticket.queue_id == queue_id,
                    Ticket.terminal_id == terminal_id,
                    Ticket.status.in_([TicketStatus.CALLED.value, TicketStatus.SERVING.value]),
                )
                .order_by(Ticket.called_at.desc())
                .limit(1)
            )
        elapsed = None
        if current and current.service_started_at:
            elapsed = int((utcnow() - current.service_started_at).total_seconds())
        elif current and current.called_at:
            elapsed = int((utcnow() - current.called_at).total_seconds())
        return {
            **status,
            "terminal_id": terminal_id,
            "serving": self.ticket_to_dict(current) if current else None,
            "elapsed_seconds": elapsed,
        }

    def _duration_seconds(self, start: datetime | None, end: datetime | None) -> int | None:
        if not start or not end:
            return None
        return max(0, int((end - start).total_seconds()))

    def ticket_detail(self, ticket_id: str) -> dict[str, Any]:
        ticket = self.get_ticket(ticket_id)
        events = self.db.scalars(
            select(TicketEvent).where(TicketEvent.ticket_id == ticket_id).order_by(TicketEvent.event_at.asc())
        ).all()
        end_at = ticket.completed_at or ticket.no_show_at or ticket.cancelled_at
        wait_end = ticket.called_at or end_at
        payload = self.ticket_to_dict(ticket)
        payload["timings"] = {
            "wait_seconds": self._duration_seconds(ticket.issued_at, wait_end),
            "service_seconds": self._duration_seconds(ticket.service_started_at, ticket.completed_at),
            "total_seconds": self._duration_seconds(ticket.issued_at, end_at or ticket.service_started_at or ticket.called_at),
        }
        payload["events"] = [
            {
                "id": e.id,
                "event_type": e.event_type,
                "event_at": e.event_at.isoformat(),
                "operator_id": e.operator_id,
                "terminal_id": e.terminal_id,
                "metadata": e.metadata_json,
            }
            for e in events
        ]
        return payload

    def queue_settings(self, queue_id: str) -> dict[str, Any]:
        queue = self.db.scalar(
            select(Queue).options(joinedload(Queue.priority_rule)).where(Queue.id == queue_id)
        )
        if not queue:
            raise NotFoundError("Fila não encontrada")
        rule = queue.priority_rule
        return {
            "id": queue.id,
            "department_id": queue.department_id,
            "name": queue.name,
            "status": queue.status,
            "normal_prefix": queue.normal_prefix,
            "priority_prefix": queue.priority_prefix,
            "digits": queue.digits,
            "initial_number": queue.initial_number,
            "final_number": queue.final_number,
            "reset_policy": queue.reset_policy,
            "priority_strategy": queue.priority_strategy,
            "kiosk_enabled": queue.kiosk_enabled,
            "kiosk_token": queue.kiosk_token,
            "department_display_name": queue.department_display_name,
            "priority_rule": {
                "normal_weight": rule.normal_weight if rule else 3,
                "priority_weight": rule.priority_weight if rule else 1,
                "priority_max_wait_seconds": rule.priority_max_wait_seconds if rule else 600,
                "normal_max_wait_seconds": rule.normal_max_wait_seconds if rule else None,
                "active": rule.active if rule else True,
            },
        }

    def list_history(
        self,
        *,
        queue_id: str | None = None,
        status: str | None = None,
        ticket_type: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = max(1, min(limit, 200))
        offset = max(0, offset)
        filters = []
        if queue_id:
            filters.append(Ticket.queue_id == queue_id)
        if status:
            filters.append(Ticket.status == status.upper())
        if ticket_type:
            filters.append(Ticket.ticket_type == ticket_type.upper())
        if search:
            like = f"%{search.strip().upper()}%"
            filters.append(Ticket.display_number.ilike(like))

        total = self.db.scalar(select(func.count()).select_from(Ticket).where(*filters)) or 0
        rows = self.db.scalars(
            select(Ticket).where(*filters).order_by(Ticket.issued_at.desc()).offset(offset).limit(limit)
        ).all()
        items = []
        for t in rows:
            item = self.ticket_to_dict(t)
            wait_end = t.called_at or t.completed_at or t.no_show_at or t.cancelled_at
            item["wait_seconds"] = self._duration_seconds(t.issued_at, wait_end)
            item["service_seconds"] = self._duration_seconds(t.service_started_at, t.completed_at)
            items.append(item)
        return {"total": total, "limit": limit, "offset": offset, "items": items}

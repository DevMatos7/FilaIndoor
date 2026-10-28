from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass(frozen=True)
class TicketCandidate:
    id: str
    ticket_type: str
    issued_at: datetime
    display_number: str


@dataclass(frozen=True)
class PriorityRules:
    normal_weight: int = 3
    priority_weight: int = 1
    priority_max_wait_seconds: int | None = 600
    normal_max_wait_seconds: int | None = None


PRIORITY_TYPES = frozenset({"PRIORITY", "PRIORITY_PLUS"})


def is_priority(ticket_type: str) -> bool:
    return ticket_type in PRIORITY_TYPES


def wait_seconds(ticket: TicketCandidate, now: datetime | None = None) -> float:
    ref = now or _utcnow()
    return max(0.0, (ref - ticket.issued_at).total_seconds())


class QueueSelectionPolicy(ABC):
    @abstractmethod
    def select_next(
        self,
        tickets: Sequence[TicketCandidate],
        rules: PriorityRules,
        *,
        recent_call_types: Sequence[str] | None = None,
        now: datetime | None = None,
    ) -> TicketCandidate | None:
        raise NotImplementedError


class FIFOQueuePolicy(QueueSelectionPolicy):
    def select_next(
        self,
        tickets: Sequence[TicketCandidate],
        rules: PriorityRules,
        *,
        recent_call_types: Sequence[str] | None = None,
        now: datetime | None = None,
    ) -> TicketCandidate | None:
        if not tickets:
            return None
        return sorted(tickets, key=lambda t: (t.issued_at, t.display_number))[0]


class WeightedPriorityPolicy(QueueSelectionPolicy):
    """Intercala normal_weight normais para cada priority_weight prioritárias."""

    def select_next(
        self,
        tickets: Sequence[TicketCandidate],
        rules: PriorityRules,
        *,
        recent_call_types: Sequence[str] | None = None,
        now: datetime | None = None,
    ) -> TicketCandidate | None:
        if not tickets:
            return None

        normals = sorted(
            [t for t in tickets if not is_priority(t.ticket_type)],
            key=lambda t: (t.issued_at, t.display_number),
        )
        priorities = sorted(
            [t for t in tickets if is_priority(t.ticket_type)],
            key=lambda t: (t.issued_at, t.display_number),
        )

        if not priorities:
            return normals[0] if normals else None
        if not normals:
            return priorities[0]

        normal_w = max(1, rules.normal_weight)
        priority_w = max(1, rules.priority_weight)
        cycle = normal_w + priority_w

        recent = list(recent_call_types or [])
        # Posição no ciclo com base nas últimas chamadas do ciclo atual
        streak_window = recent[-cycle:] if recent else []
        normals_in_window = sum(1 for t in streak_window if not is_priority(t))
        priorities_in_window = sum(1 for t in streak_window if is_priority(t))

        # Se ainda faltam normais no ciclo, chama normal; senão prioritária
        if normals_in_window < normal_w and normals:
            return normals[0]
        if priorities_in_window < priority_w and priorities:
            return priorities[0]
        # Novo ciclo: preferir normal se houver
        if normals:
            return normals[0]
        return priorities[0]


class MaxWaitPolicy(QueueSelectionPolicy):
    """Override: se prioritária (ou normal) ultrapassou limite, ela tem preferência."""

    def __init__(self, fallback: QueueSelectionPolicy):
        self.fallback = fallback

    def select_next(
        self,
        tickets: Sequence[TicketCandidate],
        rules: PriorityRules,
        *,
        recent_call_types: Sequence[str] | None = None,
        now: datetime | None = None,
    ) -> TicketCandidate | None:
        if not tickets:
            return None

        ref = now or _utcnow()

        if rules.priority_max_wait_seconds is not None:
            overdue_priority = [
                t
                for t in tickets
                if is_priority(t.ticket_type) and wait_seconds(t, ref) >= rules.priority_max_wait_seconds
            ]
            if overdue_priority:
                return sorted(overdue_priority, key=lambda t: (t.issued_at, t.display_number))[0]

        if rules.normal_max_wait_seconds is not None:
            overdue_normal = [
                t
                for t in tickets
                if not is_priority(t.ticket_type) and wait_seconds(t, ref) >= rules.normal_max_wait_seconds
            ]
            if overdue_normal:
                return sorted(overdue_normal, key=lambda t: (t.issued_at, t.display_number))[0]

        return self.fallback.select_next(
            tickets, rules, recent_call_types=recent_call_types, now=ref
        )


class QueueSelectionEngine:
    """Fachada usada pelos services — nunca pela rota HTTP diretamente."""

    def __init__(self, strategy: str = "WEIGHTED"):
        self.strategy = strategy.upper()

    def _base_policy(self) -> QueueSelectionPolicy:
        if self.strategy == "FIFO":
            return FIFOQueuePolicy()
        return WeightedPriorityPolicy()

    def select_next(
        self,
        tickets: Sequence[TicketCandidate],
        rules: PriorityRules,
        *,
        recent_call_types: Sequence[str] | None = None,
        now: datetime | None = None,
    ) -> TicketCandidate | None:
        policy: QueueSelectionPolicy = MaxWaitPolicy(self._base_policy())
        return policy.select_next(tickets, rules, recent_call_types=recent_call_types, now=now)

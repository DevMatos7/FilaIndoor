from datetime import datetime, timedelta

from app.modules.queue.policies.selection import (
    FIFOQueuePolicy,
    MaxWaitPolicy,
    PriorityRules,
    QueueSelectionEngine,
    TicketCandidate,
    WeightedPriorityPolicy,
)

BASE = datetime(2026, 10, 27, 15, 0, 0)


def T(n: str, typ: str, minutes: int = 0) -> TicketCandidate:
    return TicketCandidate(
        id=n,
        ticket_type=typ,
        issued_at=BASE + timedelta(minutes=minutes),
        display_number=n,
    )


def test_fifo_oldest_first():
    tickets = [T("A002", "NORMAL", 2), T("A001", "NORMAL", 1), T("P001", "PRIORITY", 0)]
    chosen = FIFOQueuePolicy().select_next(tickets, PriorityRules())
    assert chosen is not None
    assert chosen.id == "P001"


def test_weighted_three_normal_one_priority():
    rules = PriorityRules(normal_weight=3, priority_weight=1)
    policy = WeightedPriorityPolicy()
    waiting = [
        T("A001", "NORMAL", 0),
        T("A002", "NORMAL", 1),
        T("A003", "NORMAL", 2),
        T("A004", "NORMAL", 3),
        T("P001", "PRIORITY", 4),
    ]
    recent: list[str] = []
    order = []
    for _ in range(5):
        left = [t for t in waiting if t.id not in order]
        chosen = policy.select_next(left, rules, recent_call_types=recent)
        assert chosen
        order.append(chosen.id)
        recent.append(chosen.ticket_type)
    assert order == ["A001", "A002", "A003", "P001", "A004"]


def test_max_wait_overrides_priority():
    rules = PriorityRules(normal_weight=3, priority_weight=1, priority_max_wait_seconds=600)
    now = BASE + timedelta(minutes=15)
    tickets = [
        T("A001", "NORMAL", 14),
        T("P001", "PRIORITY", 0),  # esperando 15 min
    ]
    # issued_at de P001 = BASE, wait = 15min >= 10min
    policy = MaxWaitPolicy(WeightedPriorityPolicy())
    chosen = policy.select_next(tickets, rules, recent_call_types=[], now=now)
    assert chosen is not None
    assert chosen.id == "P001"


def test_engine_weighted_default():
    engine = QueueSelectionEngine("WEIGHTED")
    tickets = [T("A001", "NORMAL", 0), T("P001", "PRIORITY", 1)]
    # now próximo da emissão — sem override de max wait
    chosen = engine.select_next(
        tickets,
        PriorityRules(),
        recent_call_types=[],
        now=BASE + timedelta(minutes=2),
    )
    assert chosen is not None
    assert chosen.id == "A001"


def test_empty_queue():
    assert QueueSelectionEngine().select_next([], PriorityRules()) is None

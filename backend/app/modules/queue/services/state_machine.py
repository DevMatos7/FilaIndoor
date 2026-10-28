from app.core.exceptions import InvalidTransitionError
from app.modules.queue.models.enums import TicketStatus

ALLOWED_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
    TicketStatus.WAITING: {TicketStatus.CALLED, TicketStatus.CANCELLED, TicketStatus.EXPIRED},
    TicketStatus.CALLED: {TicketStatus.SERVING, TicketStatus.NO_SHOW, TicketStatus.CANCELLED},
    TicketStatus.SERVING: {TicketStatus.COMPLETED, TicketStatus.CANCELLED},
    TicketStatus.COMPLETED: set(),
    TicketStatus.NO_SHOW: set(),
    TicketStatus.CANCELLED: set(),
    TicketStatus.EXPIRED: set(),
}


def ensure_transition(current: str, target: str) -> None:
    cur = TicketStatus(current)
    tgt = TicketStatus(target)
    if tgt not in ALLOWED_TRANSITIONS.get(cur, set()):
        raise InvalidTransitionError(f"Transição inválida: {cur.value} → {tgt.value}")

import enum


class QueueStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PAUSED = "PAUSED"


class TicketType(str, enum.Enum):
    NORMAL = "NORMAL"
    PRIORITY = "PRIORITY"
    PRIORITY_PLUS = "PRIORITY_PLUS"
    CUSTOM = "CUSTOM"


class TicketStatus(str, enum.Enum):
    WAITING = "WAITING"
    CALLED = "CALLED"
    SERVING = "SERVING"
    COMPLETED = "COMPLETED"
    NO_SHOW = "NO_SHOW"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class TicketEventType(str, enum.Enum):
    TICKET_CREATED = "TICKET_CREATED"
    TICKET_CALLED = "TICKET_CALLED"
    TICKET_RECALLED = "TICKET_RECALLED"
    SERVICE_STARTED = "SERVICE_STARTED"
    SERVICE_COMPLETED = "SERVICE_COMPLETED"
    TICKET_NO_SHOW = "TICKET_NO_SHOW"
    TICKET_CANCELLED = "TICKET_CANCELLED"
    TICKET_EXPIRED = "TICKET_EXPIRED"


class TicketSource(str, enum.Enum):
    KIOSK = "KIOSK"
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    API = "API"
    REAL_PLUS = "REAL_PLUS"


class PriorityStrategy(str, enum.Enum):
    FIFO = "FIFO"
    WEIGHTED = "WEIGHTED"
    MAX_WAIT = "MAX_WAIT"


class ResetPolicy(str, enum.Enum):
    DAILY = "DAILY"
    SHIFT = "SHIFT"
    MANUAL = "MANUAL"
    NEVER = "NEVER"

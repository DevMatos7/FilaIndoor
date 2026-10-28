from pydantic import BaseModel, Field


class CreateTicketRequest(BaseModel):
    type: str = Field(default="NORMAL", description="NORMAL | PRIORITY | PRIORITY_PLUS | CUSTOM")
    source: str = Field(default="KIOSK")


class CallNextRequest(BaseModel):
    terminal_id: str | None = None
    operator_id: str | None = None
    auto_complete_current: bool = True
    auto_start: bool = False


class TicketActionRequest(BaseModel):
    terminal_id: str | None = None
    operator_id: str | None = None


class QueueCreateRequest(BaseModel):
    department_id: str
    name: str
    normal_prefix: str = "A"
    priority_prefix: str = "P"
    digits: int = 3
    initial_number: int = 1
    final_number: int = 999
    reset_policy: str = "DAILY"
    priority_strategy: str = "WEIGHTED"
    normal_weight: int = 3
    priority_weight: int = 1
    priority_max_wait_seconds: int = 600
    normal_max_wait_seconds: int | None = None


class QueueUpdateRequest(BaseModel):
    name: str | None = None
    status: str | None = None
    priority_strategy: str | None = None
    normal_prefix: str | None = None
    priority_prefix: str | None = None
    reset_policy: str | None = None
    digits: int | None = None
    initial_number: int | None = None
    final_number: int | None = None
    kiosk_enabled: bool | None = None
    kiosk_token: str | None = None
    department_display_name: str | None = None
    normal_weight: int | None = None
    priority_weight: int | None = None
    priority_max_wait_seconds: int | None = None
    normal_max_wait_seconds: int | None = None

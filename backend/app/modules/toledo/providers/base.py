from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ToledoPushResult:
    ok: bool
    skipped: bool = False
    provider: str = ""
    detail: str | None = None
    raw: dict[str, Any] | None = None


@dataclass
class ToledoHistoryItem:
    external_id: str
    ticket_number: str | None
    occurred_at: datetime | None
    wait_seconds: float | None = None
    service_seconds: float | None = None
    raw: dict[str, Any] | None = None


class NativeQueueProvider:
    """
    Fonte da verdade da fila — nunca DTO Toledo no QueueEngine.

    Este provider documenta o contrato nativo; operações de senha
    continuam em QueueService.
    """

    name = "native"

    def capabilities(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "queue_source_of_truth": True,
            "supports_issue": True,
            "supports_call": True,
            "toledo_coupled": False,
        }


class ToledoBridge(ABC):
    """Side-channels Toledo — falha nunca propaga para a fila nativa."""

    name: str = "toledo"

    @abstractmethod
    def capabilities(self) -> dict[str, Any]: ...

    @abstractmethod
    def push_ticket_to_player(
        self,
        *,
        ticket_number: str,
        counter: str | None = None,
        department: str | None = None,
    ) -> ToledoPushResult: ...

    @abstractmethod
    def fetch_history(self, *, since: datetime | None = None, limit: int = 50) -> list[ToledoHistoryItem]: ...

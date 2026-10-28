from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.modules.toledo.providers import build_native_provider, build_toledo_provider
from app.modules.toledo.providers.base import ToledoPushResult
from app.modules.toledo.service import ToledoService


class ToledoBridgeService:
    """
    Orquestra side-effects Toledo sem acoplar QueueEngine.

    Uso típico após chamada nativa:
        ToledoBridgeService(db).notify_call_safe(ticket_number=...)
    """

    def __init__(self, db: Session):
        self.db = db
        self.native = build_native_provider()
        discovery = ToledoService(db).get_discovery()
        caps = discovery.get("confirmed_capabilities") or {}
        # mapear flags do checklist
        confirmed = {
            "player_push": bool(caps.get("player_push") or discovery.get("api_enabled")),
            "history": bool(caps.get("history") or discovery.get("api_enabled")),
        }
        # se discovery diz api_enabled false, não confirma
        if discovery.get("api_enabled") is False:
            confirmed = {"player_push": False, "history": False}
        self.toledo = build_toledo_provider(confirmed=confirmed)

    def describe(self) -> dict[str, Any]:
        return {
            "native": self.native.capabilities(),
            "toledo": self.toledo.capabilities(),
            "rule": "QueueEngine nunca recebe DTO Toledo; falha Toledo não bloqueia fila",
        }

    def notify_call_safe(
        self,
        *,
        ticket_number: str,
        counter: str | None = None,
        department: str | None = None,
    ) -> ToledoPushResult:
        try:
            return self.toledo.push_ticket_to_player(
                ticket_number=ticket_number,
                counter=counter,
                department=department,
            )
        except Exception as exc:  # noqa: BLE001
            return ToledoPushResult(ok=False, skipped=False, provider="toledo", detail=str(exc)[:300])

    def sync_history_safe(self, limit: int = 50) -> dict[str, Any]:
        try:
            items = self.toledo.fetch_history(limit=limit)
            return {
                "ok": True,
                "count": len(items),
                "items": [
                    {
                        "external_id": i.external_id,
                        "ticket_number": i.ticket_number,
                        "occurred_at": i.occurred_at.isoformat() + "Z" if i.occurred_at else None,
                        "wait_seconds": i.wait_seconds,
                        "service_seconds": i.service_seconds,
                    }
                    for i in items
                ],
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "count": 0, "items": [], "detail": str(exc)[:300]}

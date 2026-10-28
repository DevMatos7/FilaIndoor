from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.modules.toledo.providers.base import ToledoBridge, ToledoHistoryItem, ToledoPushResult


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ToledoProvider(ToledoBridge):
    """
    Adapter HTTP — somente capacidades confirmadas no discovery / config.

    Endpoints não confirmados → skipped (não erro fatal).
    Erros de rede → ok=False, sem raise para a fila.
    """

    name = "toledo"

    def __init__(
        self,
        *,
        enabled: bool = False,
        mode: str = "NATIVE",
        base_url: str | None = None,
        api_key: str | None = None,
        mock: bool = False,
        confirmed: dict[str, bool] | None = None,
        timeout: float = 8.0,
    ) -> None:
        self.enabled = enabled
        self.mode = (mode or "NATIVE").upper()
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key or ""
        self.mock = mock
        self.confirmed = confirmed or {}
        self.timeout = timeout

    def capabilities(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "enabled": self.enabled,
            "mode": self.mode,
            "mock": self.mock,
            "configured": bool(self.base_url and self.api_key) or self.mock,
            "confirmed": {
                "player_push": self._cap("player_push"),
                "history": self._cap("history"),
            },
            "queue_source_of_truth": False,
            "never_blocks_native": True,
        }

    def _cap(self, key: str) -> bool:
        if self.mock:
            return True
        if not self.enabled or self.mode == "NATIVE":
            return False
        if key == "player_push" and self.mode in {"TOLEDO_DISPLAY", "TOLEDO_FULL"}:
            return bool(self.confirmed.get("player_push")) and bool(self.base_url and self.api_key)
        if key == "history" and self.mode in {"TOLEDO_SYNC", "TOLEDO_FULL"}:
            return bool(self.confirmed.get("history")) and bool(self.base_url and self.api_key)
        return False

    def push_ticket_to_player(
        self,
        *,
        ticket_number: str,
        counter: str | None = None,
        department: str | None = None,
    ) -> ToledoPushResult:
        if not self._cap("player_push"):
            return ToledoPushResult(
                ok=True,
                skipped=True,
                provider=self.name,
                detail="player_push não confirmado ou modo não permite",
            )
        payload = {
            "ticket": ticket_number,
            "counter": counter,
            "department": department,
        }
        if self.mock:
            return ToledoPushResult(ok=True, skipped=False, provider="toledo_mock", detail="mock push", raw=payload)
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/players/display",
                    headers=self._headers(),
                    json=payload,
                )
                if resp.status_code >= 400:
                    return ToledoPushResult(
                        ok=False,
                        provider=self.name,
                        detail=f"HTTP {resp.status_code}",
                        raw={"body": resp.text[:300]},
                    )
                return ToledoPushResult(ok=True, provider=self.name, detail="pushed", raw=resp.json() if resp.content else payload)
        except Exception as exc:  # noqa: BLE001 — nunca derruba a fila
            return ToledoPushResult(ok=False, provider=self.name, detail=str(exc)[:300])

    def fetch_history(self, *, since: datetime | None = None, limit: int = 50) -> list[ToledoHistoryItem]:
        if not self._cap("history"):
            return []
        if self.mock:
            return [
                ToledoHistoryItem(
                    external_id="mock-1",
                    ticket_number="A001",
                    occurred_at=_utcnow(),
                    wait_seconds=120,
                    service_seconds=90,
                    raw={"mock": True},
                )
            ]
        params: dict[str, Any] = {"limit": limit}
        if since:
            params["since"] = since.isoformat()
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(
                    f"{self.base_url}/history",
                    headers=self._headers(),
                    params=params,
                )
                if resp.status_code >= 400:
                    return []
                data = resp.json()
                rows = data if isinstance(data, list) else data.get("items") or []
                out: list[ToledoHistoryItem] = []
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    out.append(
                        ToledoHistoryItem(
                            external_id=str(row.get("id") or row.get("external_id") or ""),
                            ticket_number=row.get("ticket") or row.get("ticket_number"),
                            occurred_at=_parse_dt(row.get("occurred_at") or row.get("timestamp")),
                            wait_seconds=_num(row.get("wait_seconds")),
                            service_seconds=_num(row.get("service_seconds")),
                            raw=row,
                        )
                    )
                return out
        except Exception:  # noqa: BLE001
            return []

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "X-Integration-Key": self.api_key,
            "Accept": "application/json",
        }


def _num(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    try:
        return datetime.fromisoformat(str(value).replace("Z", ""))
    except ValueError:
        return None

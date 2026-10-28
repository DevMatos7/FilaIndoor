from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class RealtimeHub:
    """Fan-out WebSocket por loja (store_id)."""

    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, store_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._rooms.setdefault(store_id, set()).add(websocket)
        logger.info("ws connected store=%s clients=%s", store_id, len(self._rooms.get(store_id, ())))

    async def disconnect(self, store_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            clients = self._rooms.get(store_id)
            if not clients:
                return
            clients.discard(websocket)
            if not clients:
                self._rooms.pop(store_id, None)

    async def broadcast(self, store_id: str, event: str, data: dict[str, Any]) -> None:
        payload = {
            "event": event,
            "event_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        async with self._lock:
            clients = list(self._rooms.get(store_id, set()))
        dead: list[WebSocket] = []
        for ws in clients:
            try:
                await ws.send_json(payload)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            await self.disconnect(store_id, ws)

    def publish(self, store_id: str, event: str, data: dict[str, Any]) -> None:
        """Thread-safe: agenda broadcast no loop principal da API."""
        coro = self.broadcast(store_id, event, data)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
            return
        except RuntimeError:
            pass
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, self._loop)
            return
        logger.debug("publish skipped (no event loop) event=%s", event)


hub = RealtimeHub()

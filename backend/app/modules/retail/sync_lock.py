"""Postgres advisory lock for retail sync concurrency (multi-worker safe)."""

from __future__ import annotations

import hashlib
import logging
import threading
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_memory_locks: dict[str, threading.Lock] = {}
_memory_guard = threading.Lock()


def _lock_key(store_id: str, entity: str) -> int:
    digest = hashlib.sha256(f"retail-sync:{store_id}:{entity}".encode()).digest()
    return int.from_bytes(digest[:8], "big") & 0x7FFFFFFFFFFFFFFF


def _memory_lock(store_id: str, entity: str) -> threading.Lock:
    key = f"{store_id}:{entity.upper()}"
    with _memory_guard:
        if key not in _memory_locks:
            _memory_locks[key] = threading.Lock()
        return _memory_locks[key]


@contextmanager
def retail_sync_lock(db: Session, store_id: str, entity: str) -> Iterator[bool]:
    """
    Try advisory lock. Yields True if acquired, False if already held.

    Postgres: dedicated connection + pg_try_advisory_lock so Session.commit()
    inside the sync cannot return a pooled connection that still holds the lock.
    SQLite/tests: threading.Lock fallback.
    """
    settings = get_settings()
    use_pg = settings.database_url.startswith("postgresql")
    if not use_pg:
        lock = _memory_lock(store_id, entity)
        acquired = lock.acquire(blocking=False)
        if not acquired:
            logger.info("retail.sync.lock_skip store=%s entity=%s", store_id, entity)
            yield False
            return
        try:
            yield True
        finally:
            lock.release()
        return

    key = _lock_key(store_id, entity.upper())
    # IMPORTANT: hold lock on a dedicated connection for the whole critical section.
    # Session.commit() during sync would otherwise recycle a pooled connection that
    # still owns a session-level advisory lock → permanent SKIPPED for that entity.
    bind = db.get_bind()
    conn = bind.connect()
    try:
        acquired = bool(conn.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": key}).scalar())
        if not acquired:
            logger.info("retail.sync.lock_skip store=%s entity=%s", store_id, entity)
            yield False
            return
        logger.info("retail.sync.lock_acquired store=%s entity=%s", store_id, entity)
        try:
            yield True
        finally:
            try:
                conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": key})
                conn.commit()
            except Exception:  # noqa: BLE001
                logger.exception("retail.sync.lock_release_failed store=%s entity=%s", store_id, entity)
            logger.info("retail.sync.lock_released store=%s entity=%s", store_id, entity)
    finally:
        conn.close()

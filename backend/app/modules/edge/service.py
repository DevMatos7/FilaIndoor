from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.edge.models import EdgeOutboxEvent
from app.modules.org.models.entities import Department, Store
from app.modules.queue.models.entities import Display, Queue, utcnow
from app.modules.signage.models import MediaAsset, Playlist
from app.modules.signage.playlist_service import PlaylistService

SYNC_STATUSES = {"PENDING", "SYNCED", "FAILED"}
PROCESSABLE_TYPES = {"TICKET_ISSUE", "TELEMETRY", "CACHE_HIT", "GENERIC", "TICKET_ISSUED", "TICKET_CALLED"}


def _event_dict(ev: EdgeOutboxEvent) -> dict[str, Any]:
    return {
        "id": ev.id,
        "event_id": ev.event_id,
        "store_id": ev.store_id,
        "origin_device": ev.origin_device,
        "origin_edge": ev.origin_edge,
        "event_type": ev.event_type,
        "payload": ev.payload or {},
        "occurred_at": ev.occurred_at.isoformat() + "Z" if ev.occurred_at else None,
        "sync_status": ev.sync_status,
        "attempts": ev.attempts,
        "last_error": ev.last_error,
        "synced_at": ev.synced_at.isoformat() + "Z" if ev.synced_at else None,
    }


class EdgeService:
    def __init__(self, db: Session, edge_name: str = "store-edge"):
        self.db = db
        self.edge_name = edge_name

    def health(self) -> dict[str, Any]:
        pending = self.db.scalar(
            select(func.count()).select_from(EdgeOutboxEvent).where(EdgeOutboxEvent.sync_status == "PENDING")
        )
        failed = self.db.scalar(
            select(func.count()).select_from(EdgeOutboxEvent).where(EdgeOutboxEvent.sync_status == "FAILED")
        )
        return {
            "status": "ok",
            "mode": "edge",
            "edge": self.edge_name,
            "offline_capable": True,
            "outbox": {"pending": int(pending or 0), "failed": int(failed or 0)},
            "timestamp": utcnow().isoformat() + "Z",
        }

    def sync_status(self, store_id: str | None = None) -> dict[str, Any]:
        stmt = select(EdgeOutboxEvent.sync_status, func.count()).group_by(EdgeOutboxEvent.sync_status)
        if store_id:
            stmt = stmt.where(EdgeOutboxEvent.store_id == store_id)
        rows = self.db.execute(stmt).all()
        counts = {status: 0 for status in SYNC_STATUSES}
        for status, count in rows:
            counts[status] = int(count)
        return {
            "store_id": store_id,
            "edge": self.edge_name,
            "counts": counts,
            "pending": counts["PENDING"],
            "failed": counts["FAILED"],
            "synced": counts["SYNCED"],
        }

    def list_events(
        self,
        *,
        store_id: str | None = None,
        sync_status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        stmt = select(EdgeOutboxEvent).order_by(EdgeOutboxEvent.occurred_at.desc()).limit(min(limit, 200))
        if store_id:
            stmt = stmt.where(EdgeOutboxEvent.store_id == store_id)
        if sync_status:
            stmt = stmt.where(EdgeOutboxEvent.sync_status == sync_status)
        return [_event_dict(e) for e in self.db.scalars(stmt).all()]

    def enqueue(
        self,
        *,
        event_id: str,
        store_id: str,
        event_type: str,
        payload: dict | None = None,
        origin_device: str | None = None,
        origin_edge: str | None = None,
        occurred_at: datetime | None = None,
    ) -> dict[str, Any]:
        event_id = (event_id or "").strip()
        if not event_id:
            raise ValidationError("event_id obrigatório")
        if not self.db.get(Store, store_id):
            raise NotFoundError("Loja não encontrada")
        event_type = (event_type or "GENERIC").upper()

        existing = self.db.scalar(select(EdgeOutboxEvent).where(EdgeOutboxEvent.event_id == event_id))
        if existing:
            return {**_event_dict(existing), "deduplicated": True}

        ev = EdgeOutboxEvent(
            event_id=event_id,
            store_id=store_id,
            event_type=event_type,
            payload=payload or {},
            origin_device=origin_device,
            origin_edge=origin_edge or self.edge_name,
            occurred_at=occurred_at or utcnow(),
            sync_status="PENDING",
        )
        self.db.add(ev)
        self.db.commit()
        self.db.refresh(ev)
        return {**_event_dict(ev), "deduplicated": False}

    def enqueue_many(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        results = []
        for item in events:
            results.append(
                self.enqueue(
                    event_id=item["event_id"],
                    store_id=item["store_id"],
                    event_type=item.get("event_type", "GENERIC"),
                    payload=item.get("payload"),
                    origin_device=item.get("origin_device"),
                    origin_edge=item.get("origin_edge"),
                )
            )
        return {"accepted": len(results), "events": results}

    def flush(self, *, store_id: str | None = None, limit: int = 50) -> dict[str, Any]:
        """Simula sync com a nuvem: PENDING → SYNCED (com retry em FAILED)."""
        stmt = (
            select(EdgeOutboxEvent)
            .where(EdgeOutboxEvent.sync_status.in_(("PENDING", "FAILED")))
            .order_by(EdgeOutboxEvent.occurred_at.asc())
            .limit(min(limit, 200))
        )
        if store_id:
            stmt = stmt.where(EdgeOutboxEvent.store_id == store_id)
        rows = list(self.db.scalars(stmt).all())
        synced = 0
        failed = 0
        details: list[dict[str, Any]] = []
        for ev in rows:
            ev.attempts = int(ev.attempts or 0) + 1
            try:
                self._apply_cloud_sync(ev)
                ev.sync_status = "SYNCED"
                ev.synced_at = utcnow()
                ev.last_error = None
                synced += 1
                details.append({"event_id": ev.event_id, "status": "SYNCED"})
            except Exception as exc:  # noqa: BLE001 — outbox não pode derrubar o flush
                ev.sync_status = "FAILED"
                ev.last_error = str(exc)[:500]
                failed += 1
                details.append({"event_id": ev.event_id, "status": "FAILED", "error": ev.last_error})
        self.db.commit()
        return {"synced": synced, "failed": failed, "processed": len(rows), "details": details}

    def retry_failed(self, store_id: str | None = None) -> dict[str, Any]:
        stmt = select(EdgeOutboxEvent).where(EdgeOutboxEvent.sync_status == "FAILED")
        if store_id:
            stmt = stmt.where(EdgeOutboxEvent.store_id == store_id)
        for ev in self.db.scalars(stmt).all():
            ev.sync_status = "PENDING"
            ev.last_error = None
        self.db.commit()
        return self.flush(store_id=store_id)

    def snapshot(self, store_id: str) -> dict[str, Any]:
        store = self.db.get(Store, store_id)
        if not store:
            raise NotFoundError("Loja não encontrada")

        depts = self.db.scalars(select(Department).where(Department.store_id == store_id)).all()
        dept_ids = [d.id for d in depts]
        queues = []
        if dept_ids:
            for q in self.db.scalars(select(Queue).where(Queue.department_id.in_(dept_ids))).all():
                queues.append(
                    {
                        "id": q.id,
                        "name": q.name,
                        "status": q.status,
                        "department_id": q.department_id,
                        "kiosk_enabled": q.kiosk_enabled,
                        "normal_prefix": q.normal_prefix,
                        "priority_prefix": q.priority_prefix,
                    }
                )

        displays = [
            {
                "id": d.id,
                "name": d.name,
                "code": d.code,
                "queue_id": d.queue_id,
                "playlist_id": d.playlist_id,
                "channel_id": d.channel_id,
                "audio_enabled": d.audio_enabled,
            }
            for d in self.db.scalars(select(Display).where(Display.store_id == store_id)).all()
        ]

        playlists = []
        pl_svc = PlaylistService(self.db)
        for pl in self.db.scalars(select(Playlist).where(Playlist.store_id == store_id, Playlist.active.is_(True))).all():
            detail = pl_svc.get(pl.id)
            playlists.append(
                {
                    "id": pl.id,
                    "name": pl.name,
                    "is_default": pl.is_default,
                    "items": detail.get("items") or [],
                }
            )

        assets = [
            {
                "id": a.id,
                "name": a.name,
                "media_type": a.media_type,
                "public_url": a.public_url,
                "duration_seconds": a.duration_seconds,
                "mime_type": a.mime_type,
            }
            for a in self.db.scalars(
                select(MediaAsset).where(MediaAsset.store_id == store_id, MediaAsset.active.is_(True))
            ).all()
        ]

        return {
            "store_id": store_id,
            "store_name": store.name,
            "edge": self.edge_name,
            "generated_at": utcnow().isoformat() + "Z",
            "queues": queues,
            "displays": displays,
            "playlists": playlists,
            "assets": assets,
            "cache_ttl_seconds": 300,
        }

    def _apply_cloud_sync(self, ev: EdgeOutboxEvent) -> None:
        # MVP: sync idempotente — evento já está no edge; "nuvem" apenas confirma.
        if ev.event_type not in PROCESSABLE_TYPES and not ev.event_type:
            raise ValidationError(f"event_type desconhecido: {ev.event_type}")
        # Sem efeito colateral adicional — a fonte da verdade local já persiste a operação.
        return

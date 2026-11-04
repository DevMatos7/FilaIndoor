"""Screen Override Engine (UX-6C)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.modules.org.models.entities import Department
from app.modules.queue.models.entities import Display, Queue, utcnow
from app.modules.realtime.hub import hub
from app.modules.signage.models import Channel, MediaAsset, ScreenOverride
from app.modules.signage.override_priority import (
    ADMIN_CREATABLE_TYPES,
    OVERRIDE_TYPES,
    QUEUE_CALL_DURATION_SECONDS,
    TARGET_SCOPES,
    priority_for,
)

logger = logging.getLogger(__name__)


def _iso(dt: datetime | None) -> str | None:
    if not dt:
        return None
    return dt.isoformat() + "Z"


def serialize_override(row: ScreenOverride) -> dict[str, Any]:
    return {
        "id": row.id,
        "store_id": row.store_id,
        "override_type": row.override_type,
        "priority": row.priority,
        "target_scope": row.target_scope,
        "target_id": row.target_id,
        "payload": row.payload or {},
        "starts_at": _iso(row.starts_at),
        "expires_at": _iso(row.expires_at),
        "cancelled_at": _iso(row.cancelled_at),
        "dedupe_key": row.dedupe_key,
        "source_type": row.source_type,
        "source_id": row.source_id,
        "created_by_user_id": row.created_by_user_id,
        "created_at": _iso(row.created_at),
    }


class ScreenOverrideService:
    def __init__(self, db: Session):
        self.db = db

    def _validate_target(self, *, store_id: str, target_scope: str, target_id: str | None) -> None:
        scope = (target_scope or "").upper()
        if scope not in TARGET_SCOPES:
            raise ValidationError(f"target_scope inválido: {target_scope}")
        if scope == "STORE":
            if target_id:
                raise ValidationError("STORE não deve ter target_id")
            return
        if not target_id:
            raise ValidationError(f"{scope} exige target_id")

        if scope == "QUEUE":
            q = self.db.get(Queue, target_id)
            if not q:
                raise NotFoundError("Fila não encontrada")
            dept = self.db.get(Department, q.department_id)
            if not dept or dept.store_id != store_id:
                raise ForbiddenError("Fila não pertence à loja")
        elif scope == "DISPLAY":
            d = self.db.get(Display, target_id)
            if not d:
                raise NotFoundError("Display não encontrado")
            if d.store_id != store_id:
                raise ForbiddenError("Display não pertence à loja")
        elif scope == "CHANNEL":
            ch = self.db.get(Channel, target_id)
            if not ch:
                raise NotFoundError("Canal não encontrado")
            if ch.store_id != store_id:
                raise ForbiddenError("Canal não pertence à loja")

    def _enrich_media(self, *, store_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        asset_id = payload.get("media_asset_id")
        if not asset_id:
            return payload
        asset = self.db.get(MediaAsset, asset_id)
        if not asset or asset.store_id != store_id:
            raise ValidationError("media_asset_id inválido para a loja")
        payload = dict(payload)
        payload["media_url"] = asset.public_url
        payload["media_type"] = asset.media_type
        payload["mime_type"] = asset.mime_type
        return payload

    def _validate_payload(self, override_type: str, payload: dict[str, Any], *, store_id: str) -> dict[str, Any]:
        p = dict(payload or {})
        t = override_type.upper()
        if t == "QUEUE_CALL":
            required = ["ticket_number", "queue_id", "department_name"]
            for k in required:
                if not p.get(k):
                    raise ValidationError(f"payload.{k} obrigatório para QUEUE_CALL")
            p.setdefault("instruction", "Dirija-se ao balcão")
        elif t == "EMERGENCY":
            if not p.get("title") and not p.get("message"):
                raise ValidationError("payload.title ou payload.message obrigatório")
            p.setdefault("title", p.get("title") or "Aviso importante")
            p.setdefault("message", p.get("message") or "")
        elif t in {"MANUAL", "CAMPAIGN"}:
            if p.get("media_asset_id"):
                p = self._enrich_media(store_id=store_id, payload=p)
            elif not p.get("title") and not p.get("message"):
                raise ValidationError("payload.title, payload.message ou media_asset_id obrigatório")
            p.setdefault("title", p.get("title") or ("Campanha" if t == "CAMPAIGN" else "Aviso"))
            p.setdefault("message", p.get("message") or "")
        else:
            raise ValidationError(f"override_type inválido: {t}")
        return p

    def create(
        self,
        *,
        store_id: str,
        override_type: str,
        target_scope: str,
        target_id: str | None = None,
        payload: dict[str, Any] | None = None,
        starts_at: datetime | None = None,
        expires_at: datetime | None = None,
        duration_seconds: int | None = None,
        dedupe_key: str | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        created_by_user_id: str | None = None,
        allow_queue_call: bool = False,
        publish_ws: bool = True,
    ) -> dict[str, Any]:
        otype = (override_type or "").upper()
        if otype not in OVERRIDE_TYPES:
            raise ValidationError(f"override_type inválido: {otype}")
        if otype == "QUEUE_CALL" and not allow_queue_call:
            raise ValidationError("QUEUE_CALL não pode ser criado via API administrativa")
        if otype not in ADMIN_CREATABLE_TYPES and not allow_queue_call:
            raise ValidationError(f"override_type não permitido: {otype}")

        if dedupe_key:
            existing = self.db.scalar(
                select(ScreenOverride).where(
                    ScreenOverride.store_id == store_id,
                    ScreenOverride.dedupe_key == dedupe_key,
                )
            )
            if existing:
                return serialize_override(existing)

        scope = (target_scope or "").upper()
        self._validate_target(store_id=store_id, target_scope=scope, target_id=target_id)
        clean_payload = self._validate_payload(otype, payload or {}, store_id=store_id)

        now = utcnow()
        start = starts_at or now
        if expires_at is None:
            secs = duration_seconds or (QUEUE_CALL_DURATION_SECONDS if otype == "QUEUE_CALL" else 60)
            expires_at = start + timedelta(seconds=max(1, int(secs)))
        if expires_at <= start:
            raise ValidationError("expires_at deve ser posterior a starts_at")

        row = ScreenOverride(
            store_id=store_id,
            override_type=otype,
            priority=priority_for(otype),
            target_scope=scope,
            target_id=None if scope == "STORE" else target_id,
            payload=clean_payload,
            starts_at=start,
            expires_at=expires_at,
            dedupe_key=dedupe_key,
            source_type=source_type,
            source_id=source_id,
            created_by_user_id=created_by_user_id,
            created_at=now,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        data = serialize_override(row)
        if publish_ws and otype != "QUEUE_CALL":
            hub.publish(store_id, "screen.override.started", {"override": data})
        return data

    def cancel(self, override_id: str, *, store_id: str | None = None) -> dict[str, Any]:
        row = self.db.get(ScreenOverride, override_id)
        if not row:
            raise NotFoundError("Override não encontrado")
        if store_id and row.store_id != store_id:
            raise ForbiddenError("Override não pertence à loja")
        if not row.cancelled_at:
            row.cancelled_at = utcnow()
            self.db.commit()
            self.db.refresh(row)
            hub.publish(row.store_id, "screen.override.cancelled", {"override_id": row.id, "override": serialize_override(row)})
        return serialize_override(row)

    def list_overrides(
        self,
        *,
        store_id: str,
        active: bool | None = None,
        override_type: str | None = None,
        target_scope: str | None = None,
        target_id: str | None = None,
    ) -> list[dict[str, Any]]:
        now = utcnow()
        stmt = select(ScreenOverride).where(ScreenOverride.store_id == store_id)
        if override_type:
            stmt = stmt.where(ScreenOverride.override_type == override_type.upper())
        if target_scope:
            stmt = stmt.where(ScreenOverride.target_scope == target_scope.upper())
        if target_id:
            stmt = stmt.where(ScreenOverride.target_id == target_id)
        rows = list(self.db.scalars(stmt.order_by(ScreenOverride.created_at.desc())).all())
        if active is True:
            rows = [
                r
                for r in rows
                if r.cancelled_at is None and r.starts_at <= now < r.expires_at
            ]
        elif active is False:
            rows = [
                r
                for r in rows
                if r.cancelled_at is not None or r.starts_at > now or r.expires_at <= now
            ]
        return [serialize_override(r) for r in rows]

    def matches_display(self, row: ScreenOverride, display: Display) -> bool:
        scope = row.target_scope
        if scope == "STORE":
            return row.store_id == display.store_id
        if scope == "QUEUE":
            return bool(display.queue_id) and row.target_id == display.queue_id
        if scope == "DISPLAY":
            return row.target_id == display.id
        if scope == "CHANNEL":
            return bool(display.channel_id) and row.target_id == display.channel_id
        return False

    def resolve_active_for_display(self, display: Display) -> list[dict[str, Any]]:
        now = utcnow()
        rows = list(
            self.db.scalars(
                select(ScreenOverride).where(
                    ScreenOverride.store_id == display.store_id,
                    ScreenOverride.cancelled_at.is_(None),
                    ScreenOverride.starts_at <= now,
                    ScreenOverride.expires_at > now,
                )
            ).all()
        )
        matched = [r for r in rows if self.matches_display(r, display)]
        matched.sort(key=lambda r: (-r.priority, -r.starts_at.timestamp(), -r.created_at.timestamp()))
        return [serialize_override(r) for r in matched]

    def create_queue_call_from_ticket(
        self,
        *,
        store_id: str,
        queue_id: str,
        ticket: dict[str, Any],
        department: str,
        event: str,
    ) -> dict[str, Any] | None:
        """Best-effort — never raise to caller of queue lifecycle."""
        try:
            ticket_id = ticket.get("id") or "unknown"
            number = ticket.get("number") or ""
            suffix = uuid4().hex[:12]
            dedupe = f"{event}:{ticket_id}:{suffix}"
            return self.create(
                store_id=store_id,
                override_type="QUEUE_CALL",
                target_scope="QUEUE",
                target_id=queue_id,
                payload={
                    "ticket_id": ticket_id,
                    "ticket_number": number,
                    "queue_id": queue_id,
                    "department_name": department,
                    "ticket_type": ticket.get("type"),
                    "instruction": "Dirija-se ao balcão",
                    "event": event,
                },
                duration_seconds=QUEUE_CALL_DURATION_SECONDS,
                dedupe_key=dedupe,
                source_type="TICKET_EVENT",
                source_id=ticket_id,
                allow_queue_call=True,
                publish_ws=False,  # embedded in ticket.* event
            )
        except Exception:  # noqa: BLE001
            logger.exception("screen_override QUEUE_CALL failed (ticket still valid)")
            return None

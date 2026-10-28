from __future__ import annotations

import secrets
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.modules.queue.models.entities import Queue, Ticket, utcnow
from app.modules.queue.models.enums import TicketSource, TicketStatus
from app.modules.queue.services.queue_service import QueueService
from app.modules.real_plus.models import VirtualNotification, VirtualTicket


class RealPlusService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.queues = QueueService(db)

    def _ensure_enabled(self) -> None:
        if not self.settings.real_plus_enabled:
            raise ForbiddenError("REAL+ desabilitado (REAL_PLUS_ENABLED=false)")

    def preview(self, queue_id: str) -> dict[str, Any]:
        self._ensure_enabled()
        status = self.queues.queue_status(queue_id)
        queue = self.queues.get_queue(queue_id)
        return {
            "queue_id": queue_id,
            "name": status["name"],
            "department_name": queue.department_display_name or status["name"],
            "status": status["status"],
            "waiting_count": status["waiting_count"],
            "estimated_wait_seconds": status["estimated_wait_seconds"],
            "estimated_wait_minutes": max(1, round(status["estimated_wait_seconds"] / 60)) if status["waiting_count"] else 0,
            "real_plus": True,
        }

    def issue(
        self,
        queue_id: str,
        *,
        ticket_type: str = "NORMAL",
        customer_label: str | None = None,
        notify_when_ahead: int = 2,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        self._ensure_enabled()
        if notify_when_ahead < 0:
            raise ValidationError("notify_when_ahead inválido")
        ticket = self.queues.create_ticket(
            queue_id,
            ticket_type=ticket_type.upper(),
            source=TicketSource.REAL_PLUS.value,
            idempotency_key=idempotency_key,
        )
        token = secrets.token_urlsafe(24)
        vt = VirtualTicket(
            ticket_id=ticket["id"],
            queue_id=queue_id,
            tracking_token=token,
            customer_label=(customer_label or "").strip() or None,
            presence_status="WAITING_REMOTE",
            notify_when_ahead=notify_when_ahead,
            last_position=ticket.get("people_ahead"),
        )
        self.db.add(vt)
        self.db.flush()
        self._notify(
            vt,
            title="Senha reservada",
            body=f"Sua senha é {ticket['number']}. Acompanhe a posição neste link.",
            channel="IN_APP",
        )
        self.db.commit()
        self.db.refresh(vt)
        return self.tracking(token)

    def tracking(self, tracking_token: str) -> dict[str, Any]:
        self._ensure_enabled()
        vt = self._by_token(tracking_token)
        ticket = self.db.get(Ticket, vt.ticket_id)
        if not ticket:
            raise NotFoundError("Senha não encontrada")
        queue = self.db.get(Queue, vt.queue_id)
        people_ahead = self.queues._people_ahead(queue, ticket) if ticket.status == TicketStatus.WAITING.value else 0
        eta = self.queues.estimate_wait_seconds(queue, people_ahead) if ticket.status == TicketStatus.WAITING.value else 0

        # atualiza presença se já chamada
        if ticket.status in {TicketStatus.CALLED.value, TicketStatus.SERVING.value} and vt.presence_status not in {
            "CALLED",
            "DONE",
        }:
            vt.presence_status = "CALLED"
        if ticket.status in {TicketStatus.COMPLETED.value, TicketStatus.NO_SHOW.value, TicketStatus.CANCELLED.value}:
            vt.presence_status = "DONE"

        # notificação de proximidade na fila (faltam N)
        if (
            ticket.status == TicketStatus.WAITING.value
            and people_ahead <= vt.notify_when_ahead
            and (vt.last_notified_ahead is None or people_ahead < vt.last_notified_ahead)
        ):
            self._notify(
                vt,
                title="Quase na sua vez",
                body=f"Faltam aproximadamente {people_ahead} atendimento(s). Dirija-se ao setor e faça check-in.",
                channel="PUSH_STUB" if vt.push_endpoint else "IN_APP",
            )
            vt.last_notified_ahead = people_ahead
            if people_ahead <= vt.notify_when_ahead and vt.presence_status == "WAITING_REMOTE":
                vt.presence_status = "APPROACHING"

        vt.last_position = people_ahead
        self.db.commit()

        notes = self.db.scalars(
            select(VirtualNotification)
            .where(VirtualNotification.virtual_ticket_id == vt.id)
            .order_by(VirtualNotification.created_at.desc())
            .limit(20)
        ).all()

        return {
            "tracking_token": vt.tracking_token,
            "presence_status": vt.presence_status,
            "customer_label": vt.customer_label,
            "notify_when_ahead": vt.notify_when_ahead,
            "checked_in_at": vt.checked_in_at.isoformat() + "Z" if vt.checked_in_at else None,
            "ticket": {
                "id": ticket.id,
                "number": ticket.display_number,
                "type": ticket.ticket_type,
                "status": ticket.status,
                "people_ahead": people_ahead,
                "estimated_wait_seconds": eta,
                "estimated_wait_minutes": max(1, round(eta / 60)) if people_ahead else 0,
            },
            "queue": {
                "id": queue.id if queue else vt.queue_id,
                "name": queue.name if queue else None,
                "department_name": queue.department_display_name if queue else None,
            },
            "notifications": [
                {
                    "id": n.id,
                    "channel": n.channel,
                    "title": n.title,
                    "body": n.body,
                    "created_at": n.created_at.isoformat() + "Z",
                }
                for n in notes
            ],
            "actions": {
                "can_check_in": ticket.status == TicketStatus.WAITING.value
                and vt.presence_status in {"WAITING_REMOTE", "APPROACHING"},
                "can_subscribe_push": True,
            },
        }

    def check_in(self, tracking_token: str) -> dict[str, Any]:
        self._ensure_enabled()
        vt = self._by_token(tracking_token)
        ticket = self.db.get(Ticket, vt.ticket_id)
        if not ticket:
            raise NotFoundError("Senha não encontrada")
        if ticket.status != TicketStatus.WAITING.value:
            raise ConflictError("Check-in só é permitido enquanto a senha está aguardando")
        vt.presence_status = "CHECKED_IN"
        vt.checked_in_at = utcnow()
        self._notify(
            vt,
            title="Check-in confirmado",
            body=f"Você está na loja. Senha {ticket.display_number} permanece na fila.",
            channel="IN_APP",
        )
        self.db.commit()
        return self.tracking(tracking_token)

    def subscribe_push(self, tracking_token: str, endpoint: str | None = None) -> dict[str, Any]:
        self._ensure_enabled()
        vt = self._by_token(tracking_token)
        vt.push_endpoint = (endpoint or "stub://browser").strip()
        self._notify(
            vt,
            title="Notificações ativas",
            body="Avisaremos quando faltar pouco para o seu atendimento (push stub).",
            channel="PUSH_STUB",
        )
        self.db.commit()
        return {"ok": True, "channel": "PUSH_STUB", "endpoint": vt.push_endpoint}

    def list_virtual(self, queue_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        self._ensure_enabled()
        stmt = select(VirtualTicket).order_by(VirtualTicket.created_at.desc()).limit(min(limit, 200))
        if queue_id:
            stmt = stmt.where(VirtualTicket.queue_id == queue_id)
        rows = self.db.scalars(stmt).all()
        out = []
        for vt in rows:
            ticket = self.db.get(Ticket, vt.ticket_id)
            out.append(
                {
                    "id": vt.id,
                    "tracking_token": vt.tracking_token,
                    "presence_status": vt.presence_status,
                    "customer_label": vt.customer_label,
                    "ticket_number": ticket.display_number if ticket else None,
                    "ticket_status": ticket.status if ticket else None,
                    "checked_in_at": vt.checked_in_at.isoformat() + "Z" if vt.checked_in_at else None,
                    "created_at": vt.created_at.isoformat() + "Z",
                }
            )
        return out

    def _by_token(self, token: str) -> VirtualTicket:
        vt = self.db.scalar(select(VirtualTicket).where(VirtualTicket.tracking_token == token))
        if not vt:
            raise NotFoundError("Tracking inválido")
        return vt

    def _notify(self, vt: VirtualTicket, *, title: str, body: str, channel: str) -> None:
        self.db.add(
            VirtualNotification(
                virtual_ticket_id=vt.id,
                channel=channel,
                title=title,
                body=body,
                delivered=True,
            )
        )

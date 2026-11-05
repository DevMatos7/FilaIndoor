"""UX-10 — Screen & Device Fleet overview (read-only view model)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.modules.devices.models import Device
from app.modules.devices.service import (
    DEGRADED_SECONDS,
    DEVICE_TYPES,
    ONLINE_SECONDS,
    DeviceService,
    _compute_status,
)
from app.modules.edge.service import EdgeService
from app.modules.org.models.entities import Department
from app.modules.queue.models.entities import Display, Queue, Terminal, utcnow
from app.modules.signage.layout_service import LayoutService
from app.modules.signage.models import Channel, ScreenGroup
from app.modules.signage.override_service import ScreenOverrideService
from app.modules.signage.schedule_service import ScheduleService

TYPE_LABELS = {
    "DISPLAY": "Tela",
    "KIOSK": "Totem",
    "PRINTER": "Impressora",
    "BUTTON": "Botoeira",
    "EDGE": "Edge",
    "TERMINAL": "Terminal",
}

STATUS_LABELS = {
    "ONLINE": "Online",
    "DEGRADED": "Com atenção",
    "OFFLINE": "Offline",
    "DISABLED": "Desabilitado",
}


def _rel_last_seen(last_seen_at: datetime | None, now: datetime) -> str | None:
    if not last_seen_at:
        return None
    age = max(0, int((now - last_seen_at).total_seconds()))
    if age < 15:
        return "agora"
    if age < 60:
        return f"há {age} s"
    if age < 3600:
        return f"há {age // 60} min"
    if age < 86400:
        return f"há {age // 3600} h"
    return f"há {age // 86400} d"


class FleetService:
    def __init__(self, db: Session):
        self.db = db
        self.devices = DeviceService(db)
        self.schedules = ScheduleService(db)
        self.layouts = LayoutService(db)
        self.overrides = ScreenOverrideService(db)
        self.edge = EdgeService(db)

    def fleet(self, store_id: str) -> dict[str, Any]:
        if not store_id:
            raise ValidationError("store_id obrigatório")
        now = utcnow()
        displays = list(
            self.db.scalars(
                select(Display).where(Display.store_id == store_id).order_by(Display.name)
            ).all()
        )
        for d in displays:
            self.devices.ensure_for_display(d)

        managed = list(
            self.db.scalars(select(Device).where(Device.store_id == store_id).order_by(Device.name)).all()
        )
        by_display = {d.display_id: d for d in managed if d.display_id}

        dept_ids = {d.department_id for d in displays if d.department_id}
        dept_ids |= {d.department_id for d in managed if d.department_id}
        departments = {
            d.id: d
            for d in self.db.scalars(select(Department).where(Department.id.in_(dept_ids or {"__none__"}))).all()
        }
        queues = {
            q.id: q
            for q in self.db.scalars(
                select(Queue).where(Queue.department_id.in_({d.id for d in departments.values()} or {"__none__"}))
            ).all()
        }
        # also queues linked on display
        q_extra = {d.queue_id for d in displays if d.queue_id and d.queue_id not in queues}
        if q_extra:
            for q in self.db.scalars(select(Queue).where(Queue.id.in_(q_extra))).all():
                queues[q.id] = q

        channels = {c["id"]: c for c in self.schedules.list_channels(store_id=store_id)}
        groups = list(
            self.db.scalars(
                select(ScreenGroup).where(ScreenGroup.store_id == store_id, ScreenGroup.active.is_(True))
            ).all()
        )

        # terminals of departments in this store
        store_dept_ids = [
            d.id
            for d in self.db.scalars(select(Department).where(Department.store_id == store_id)).all()
        ]
        terminals = list(
            self.db.scalars(
                select(Terminal)
                .where(Terminal.department_id.in_(store_dept_ids or ["__none__"]))
                .order_by(Terminal.name)
            ).all()
        )

        items: list[dict[str, Any]] = []
        seen_device_ids: set[str] = set()

        for display in displays:
            device = by_display.get(display.id)
            if device:
                seen_device_ids.add(device.id)
            items.append(
                self._display_item(
                    display=display,
                    device=device,
                    departments=departments,
                    queues=queues,
                    channels=channels,
                    now=now,
                )
            )

        for device in managed:
            if device.id in seen_device_ids:
                continue
            if device.display_id:
                # display of another store shouldn't happen; skip orphan link
                continue
            items.append(self._device_item(device, departments=departments, now=now))

        for t in terminals:
            items.append(self._terminal_item(t, departments=departments))

        edge_summary = self._edge_summary(store_id)
        # synthetic EDGE card from sync status if no EDGE device enrolled
        if not any(i.get("device_type") == "EDGE" for i in items):
            items.append(
                {
                    "id": f"edge:{store_id}",
                    "fleet_kind": "EDGE_SYNC",
                    "device_id": None,
                    "display_id": None,
                    "name": "Edge da loja",
                    "device_type": "EDGE",
                    "type_label": TYPE_LABELS["EDGE"],
                    "status": edge_summary["status"],
                    "status_label": STATUS_LABELS.get(edge_summary["status"], edge_summary["status"]),
                    "active": True,
                    "last_seen_at": edge_summary.get("last_synced_at"),
                    "last_seen_relative": None,
                    "department": None,
                    "commercial_code": None,
                    "channel": None,
                    "layout": None,
                    "programmed": None,
                    "overrides": [],
                    "edge": edge_summary,
                    "search_text": "edge sincronização",
                }
            )

        summary = self._summary(items)
        return {
            "store_id": store_id,
            "at": now.isoformat() + "Z",
            "heartbeat": {
                "online_seconds": ONLINE_SECONDS,
                "degraded_seconds": DEGRADED_SECONDS,
                "note": "Mesma regra de DeviceService._compute_status / Command Center.",
            },
            "summary": summary,
            "items": items,
            "edge": edge_summary,
            "groups": [
                {
                    "id": g.id,
                    "name": g.name,
                    "channel_id": g.channel_id,
                    "channel_name": (channels.get(g.channel_id) or {}).get("name"),
                    "active": g.active,
                }
                for g in groups
            ],
            "channels": [
                {
                    "id": c["id"],
                    "name": c["name"],
                    "layout_summary": c.get("layout_summary"),
                    "default_playlist": c.get("default_playlist"),
                    "schedule_count": c.get("schedule_count"),
                }
                for c in channels.values()
            ],
            "device_types_present": sorted({i["device_type"] for i in items}),
        }

    def assign_channel(
        self, display_id: str, *, channel_id: str | None, store_id: str | None = None
    ) -> dict[str, Any]:
        display = self.db.get(Display, display_id)
        if not display:
            raise NotFoundError("Display não encontrado")
        if store_id and display.store_id != store_id:
            raise ForbiddenError("Display não pertence à loja")
        if channel_id:
            ch = self.db.get(Channel, channel_id)
            if not ch or not ch.active:
                raise NotFoundError("Canal não encontrado")
            if ch.store_id != display.store_id:
                raise ValidationError("Canal pertence a outra loja")
            display.channel_id = channel_id
        else:
            display.channel_id = None
        self.db.commit()
        self.db.refresh(display)
        DeviceService(self.db).bump_config_version(display_id=display.id)
        return self._display_public(display)

    def update_display_safe(
        self, display_id: str, *, store_id: str | None = None, **fields: Any
    ) -> dict[str, Any]:
        display = self.db.get(Display, display_id)
        if not display:
            raise NotFoundError("Display não encontrado")
        if store_id and display.store_id != store_id:
            raise ForbiddenError("Display não pertence à loja")
        if "channel_id" in fields:
            channel_id = fields["channel_id"]
            if channel_id:
                ch = self.db.get(Channel, channel_id)
                if not ch or not ch.active:
                    raise NotFoundError("Canal não encontrado")
                if ch.store_id != display.store_id:
                    raise ValidationError("Canal pertence a outra loja")
        if "screen_group_id" in fields and fields["screen_group_id"]:
            g = self.db.get(ScreenGroup, fields["screen_group_id"])
            if not g or not g.active:
                raise NotFoundError("Grupo de telas não encontrado")
            if g.store_id != display.store_id:
                raise ValidationError("Grupo pertence a outra loja")
        for key, value in fields.items():
            if hasattr(display, key):
                setattr(display, key, value)
        self.db.commit()
        self.db.refresh(display)
        if fields.keys() & {"playlist_id", "channel_id", "screen_group_id", "audio_enabled", "audio_template"}:
            DeviceService(self.db).bump_config_version(display_id=display.id)
        return self._display_public(display)

    def _display_public(self, display: Display) -> dict[str, Any]:
        return {
            "id": display.id,
            "store_id": display.store_id,
            "name": display.name,
            "code": display.code,
            "active": display.active,
            "audio_enabled": display.audio_enabled,
            "audio_template": display.audio_template,
            "queue_id": display.queue_id,
            "playlist_id": display.playlist_id,
            "channel_id": display.channel_id,
            "screen_group_id": display.screen_group_id,
            "token_configured": bool(display.token),
            # token bruto omitido propositalmente (UX-10)
        }

    def _edge_summary(self, store_id: str) -> dict[str, Any]:
        from app.modules.edge.models import EdgeOutboxEvent

        sync = self.edge.sync_status(store_id)
        failed = int(sync.get("failed") or 0)
        pending = int(sync.get("pending") or 0)
        if failed > 0 or pending > 20:
            status = "DEGRADED"
        else:
            status = "ONLINE"
        last_row = self.db.scalar(
            select(EdgeOutboxEvent.synced_at)
            .where(EdgeOutboxEvent.store_id == store_id, EdgeOutboxEvent.synced_at.is_not(None))
            .order_by(EdgeOutboxEvent.synced_at.desc())
            .limit(1)
        )
        return {
            "status": status,
            "pending": pending,
            "failed": failed,
            "synced": int(sync.get("synced") or 0),
            "last_synced_at": last_row.isoformat() + "Z" if last_row else None,
            "details_path": "/edge",
            "note": "Status derivado de outbox (failed>0 ou pending>20 → DEGRADED), mesma regra do Command Center.",
        }

    def _summary(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        # exclude synthetic edge from "device" totals? include for visibility
        physical = [i for i in items if i.get("fleet_kind") != "EDGE_SYNC"]
        def count(status: str) -> int:
            return sum(1 for i in physical if i.get("status") == status)

        by_type: dict[str, int] = {}
        for i in physical:
            by_type[i["device_type"]] = by_type.get(i["device_type"], 0) + 1
        return {
            "total": len(physical),
            "online": count("ONLINE"),
            "degraded": count("DEGRADED"),
            "offline": count("OFFLINE"),
            "disabled": count("DISABLED"),
            "attention": count("DEGRADED"),
            "by_type": by_type,
            "displays": by_type.get("DISPLAY", 0),
            "kiosks": by_type.get("KIOSK", 0),
        }

    def _display_item(
        self,
        *,
        display: Display,
        device: Device | None,
        departments: dict[str, Department],
        queues: dict[str, Queue],
        channels: dict[str, dict[str, Any]],
        now: datetime,
    ) -> dict[str, Any]:
        status = _compute_status(device) if device else ("OFFLINE" if display.active else "DISABLED")
        if device and device.status == "DISABLED":
            status = "DISABLED"
        if not display.active and status != "DISABLED":
            # administratively disabled display
            admin_disabled = True
        else:
            admin_disabled = not display.active

        channel = channels.get(display.channel_id) if display.channel_id else None
        layout = None
        programmed = None
        if channel:
            layout = channel.get("layout_summary")
            try:
                active = self.schedules.active_at(display.channel_id, now)
                programmed = {
                    "source": active.get("source"),
                    "playlist_id": active.get("playlist_id"),
                    "playlist_name": (active.get("playlist") or {}).get("name"),
                    "schedule_id": (active.get("schedule") or {}).get("id"),
                    "schedule_name": (active.get("schedule") or {}).get("name"),
                    "label": "Programado agora",
                    "confirmed": False,
                    "note": "Conteúdo esperado via ScheduleService.active_at — não é Proof of Play.",
                }
            except Exception:
                programmed = None

        overrides_raw = []
        try:
            overrides_raw = self.overrides.resolve_active_for_display(display)
        except Exception:
            overrides_raw = []
        overrides = [
            {
                "id": o.get("id"),
                "override_type": o.get("override_type"),
                "priority": o.get("priority"),
                "label": self._override_label(o.get("override_type")),
            }
            for o in overrides_raw
        ]

        dept = departments.get(display.department_id) if display.department_id else None
        queue = queues.get(display.queue_id) if display.queue_id else None
        name = display.name or (device.name if device else "Tela")
        last_seen = device.last_seen_at if device else None

        search_parts = [
            name,
            display.code or "",
            dept.name if dept else "",
            channel["name"] if channel else "",
            queue.name if queue else "",
        ]

        return {
            "id": device.id if device else f"display:{display.id}",
            "fleet_kind": "DISPLAY",
            "device_id": device.id if device else None,
            "display_id": display.id,
            "name": name,
            "device_type": "DISPLAY",
            "type_label": TYPE_LABELS["DISPLAY"],
            "status": status if not admin_disabled or status == "DISABLED" else status,
            "status_label": STATUS_LABELS.get(status, status),
            "active": display.active,
            "device_enabled": None if not device else device.status != "DISABLED",
            "last_seen_at": last_seen.isoformat() + "Z" if last_seen else None,
            "last_seen_relative": _rel_last_seen(last_seen, now),
            "department": {"id": dept.id, "name": dept.name} if dept else None,
            "queue": {"id": queue.id, "name": queue.name} if queue else None,
            "commercial_code": display.code,
            "channel": (
                {
                    "id": channel["id"],
                    "name": channel["name"],
                }
                if channel
                else None
            ),
            "layout": layout,
            "programmed": programmed,
            "overrides": overrides,
            "audio_enabled": display.audio_enabled,
            "token_configured": bool(display.token),
            "app_version": device.app_version if device else None,
            "config_version": device.config_version if device else None,
            "ip_address": device.ip_address if device else None,
            "screen_group_id": display.screen_group_id,
            "diagnostics": self._diagnostics_display(
                status=status,
                device=device,
                display=display,
                channel=channel,
                programmed=programmed,
                overrides=overrides,
                last_seen=last_seen,
                now=now,
            ),
            "search_text": " ".join(p for p in search_parts if p).lower(),
        }

    def _device_item(
        self, device: Device, *, departments: dict[str, Department], now: datetime
    ) -> dict[str, Any]:
        status = _compute_status(device)
        dept = departments.get(device.department_id) if device.department_id else None
        dtype = (device.device_type or "DISPLAY").upper()
        return {
            "id": device.id,
            "fleet_kind": "DEVICE",
            "device_id": device.id,
            "display_id": device.display_id,
            "name": device.name,
            "device_type": dtype if dtype in DEVICE_TYPES else dtype,
            "type_label": TYPE_LABELS.get(dtype, dtype),
            "status": status,
            "status_label": STATUS_LABELS.get(status, status),
            "active": device.status != "DISABLED",
            "device_enabled": device.status != "DISABLED",
            "last_seen_at": device.last_seen_at.isoformat() + "Z" if device.last_seen_at else None,
            "last_seen_relative": _rel_last_seen(device.last_seen_at, now),
            "department": {"id": dept.id, "name": dept.name} if dept else None,
            "queue": None,
            "commercial_code": None,
            "channel": None,
            "layout": None,
            "programmed": None,
            "overrides": [],
            "audio_enabled": device.audio_enabled,
            "token_configured": False,
            "app_version": device.app_version,
            "config_version": device.config_version,
            "ip_address": device.ip_address,
            "diagnostics": {
                "player": None,
                "heartbeat": {
                    "status": status,
                    "last_seen_at": device.last_seen_at.isoformat() + "Z" if device.last_seen_at else None,
                    "last_seen_relative": _rel_last_seen(device.last_seen_at, now),
                },
                "channel": None,
                "content": None,
                "overrides": [],
            },
            "search_text": f"{device.name} {dept.name if dept else ''} {dtype}".lower(),
        }

    def _terminal_item(self, t: Terminal, *, departments: dict[str, Department]) -> dict[str, Any]:
        dept = departments.get(t.department_id) if t.department_id else None
        status = "ONLINE" if t.active else "DISABLED"
        return {
            "id": f"terminal:{t.id}",
            "fleet_kind": "TERMINAL",
            "device_id": None,
            "display_id": None,
            "terminal_id": t.id,
            "name": t.name,
            "device_type": "TERMINAL",
            "type_label": TYPE_LABELS["TERMINAL"],
            "status": status,
            "status_label": "Habilitado" if t.active else "Desabilitado",
            "active": t.active,
            "device_enabled": t.active,
            "last_seen_at": None,
            "last_seen_relative": None,
            "department": {"id": dept.id, "name": dept.name} if dept else None,
            "queue": None,
            "commercial_code": t.code,
            "channel": None,
            "layout": None,
            "programmed": None,
            "overrides": [],
            "note": "Terminal operacional (sem heartbeat de Device).",
            "diagnostics": {
                "player": None,
                "heartbeat": None,
                "channel": None,
                "content": None,
                "overrides": [],
            },
            "search_text": f"{t.name} {t.code} {dept.name if dept else ''}".lower(),
        }

    def _diagnostics_display(
        self,
        *,
        status: str,
        device: Device | None,
        display: Display,
        channel: dict[str, Any] | None,
        programmed: dict[str, Any] | None,
        overrides: list[dict[str, Any]],
        last_seen: datetime | None,
        now: datetime,
    ) -> dict[str, Any]:
        return {
            "player": {
                "token_configured": bool(display.token),
                "audio_enabled": display.audio_enabled,
                "config_version": device.config_version if device else None,
                "app_version": device.app_version if device else None,
            },
            "heartbeat": {
                "status": status,
                "last_seen_at": last_seen.isoformat() + "Z" if last_seen else None,
                "last_seen_relative": _rel_last_seen(last_seen, now),
                "online_seconds": ONLINE_SECONDS,
                "degraded_seconds": DEGRADED_SECONDS,
            },
            "channel": {
                "configured": bool(channel),
                "id": channel["id"] if channel else None,
                "name": channel["name"] if channel else None,
            },
            "content": programmed,
            "layout": (channel or {}).get("layout_summary"),
            "overrides": overrides,
            "display_active": display.active,
        }

    @staticmethod
    def _override_label(override_type: str | None) -> str:
        mapping = {
            "QUEUE_CALL": "Chamada de senha",
            "EMERGENCY": "Aviso emergencial",
            "PROMO": "Promoção",
            "MESSAGE": "Mensagem",
        }
        return mapping.get((override_type or "").upper(), override_type or "Interrupção")

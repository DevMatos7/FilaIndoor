"""Command Center overview — reuses Queue / Analytics / Devices / Signage / Edge."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import NotFoundError
from app.modules.analytics.service import AnalyticsService
from app.modules.devices.service import DeviceService
from app.modules.edge.service import EdgeService
from app.modules.org.models.entities import Department, Store
from app.modules.queue.models.entities import Display, Queue, Terminal, utcnow
from app.modules.queue.services.queue_service import QueueService
from app.modules.signage.schedule_service import ScheduleService


def _severity_rank(level: str) -> int:
    return {"CRITICAL": 0, "WARNING": 1, "INFO": 2}.get(level, 9)


class OperationsService:
    def __init__(self, db: Session):
        self.db = db

    def overview(self, store_id: str) -> dict[str, Any]:
        store = self.db.get(Store, store_id)
        if not store:
            raise NotFoundError("Loja não encontrada")

        sections: dict[str, str] = {
            "metrics": "ok",
            "queues": "ok",
            "devices": "ok",
            "content": "ok",
        }

        dept_ids = list(
            self.db.scalars(select(Department.id).where(Department.store_id == store_id)).all()
        )

        queue_cards: list[dict[str, Any]] = []
        try:
            queue_cards = self._build_queues(dept_ids)
        except Exception:
            sections["queues"] = "error"
            queue_cards = []

        analytics: dict[str, Any] = {}
        try:
            analytics = AnalyticsService(self.db).summary_for_store(store_id=store_id, day=date.today())
        except Exception:
            sections["metrics"] = "error"
            analytics = {
                "kpis": {
                    "issued": 0,
                    "completed": 0,
                    "waiting": 0,
                    "serving": 0,
                    "no_show": 0,
                    "wait": {"avg_seconds": None, "p90_seconds": None},
                },
                "sla": {
                    "green": 0,
                    "yellow": 0,
                    "red": 0,
                    "unknown": 0,
                    "target_wait_seconds": 600,
                    "warning_wait_seconds": 900,
                },
                "hourly": [{"hour": h, "issued": 0, "completed": 0} for h in range(24)],
            }

        devices: list[dict[str, Any]] = []
        terminals: list[Terminal] = []
        displays: list[Display] = []
        device_health: dict[str, Any] = {
            "categories": {},
            "terminals": {"total": 0, "active": 0},
        }
        edge_block = {"status": "ONLINE", "pending": 0, "failed": 0}
        try:
            devices = DeviceService(self.db).list_devices(store_id=store_id)
            terminals = (
                list(
                    self.db.scalars(
                        select(Terminal).where(
                            Terminal.department_id.in_(dept_ids) if dept_ids else False
                        )
                    ).all()
                )
                if dept_ids
                else []
            )
            displays = list(
                self.db.scalars(
                    select(Display).where(Display.store_id == store_id).order_by(Display.name)
                ).all()
            )
            device_health = self._device_health(devices, terminals, displays)
            edge = EdgeService(self.db).sync_status(store_id=store_id)
            edge_block = {
                "pending": int(edge.get("pending") or 0),
                "failed": int(edge.get("failed") or 0),
                "status": "ONLINE",
            }
            if edge_block["failed"] > 0 or edge_block["pending"] > 20:
                edge_block["status"] = "DEGRADED"
        except Exception:
            sections["devices"] = "error"

        content: dict[str, Any] = {
            "available": False,
            "message": "Conteúdo atual indisponível",
            "items": [],
        }
        try:
            content = self._content_now(store_id, displays)
        except Exception:
            sections["content"] = "error"

        alerts = self._derive_alerts(queue_cards, devices, edge_block, analytics)
        active_terminals = sum(1 for t in terminals if t.active)

        kpis = dict(analytics.get("kpis") or {})
        # Operacional: aguardando agora = soma das filas (não inventar)
        if sections["queues"] == "ok":
            kpis["waiting"] = sum(int(q.get("waiting_count") or 0) for q in queue_cards)
            serving_now = sum(
                1
                for q in queue_cards
                if (q.get("current_status") or "").upper() in {"SERVING", "CALLED"}
            )
            kpis["serving"] = serving_now

        wait = kpis.get("wait") or {}
        public_queues = [{k: v for k, v in q.items() if k != "severity_rank"} for q in queue_cards]

        return {
            "store_id": store_id,
            "store_name": store.name,
            "generated_at": utcnow().isoformat() + "Z",
            "metrics": {
                "issued": int(kpis.get("issued") or 0),
                "completed": int(kpis.get("completed") or 0),
                "waiting": int(kpis.get("waiting") or 0),
                "serving": int(kpis.get("serving") or 0),
                "no_show": int(kpis.get("no_show") or 0),
                "active_terminals": active_terminals,
                "wait": {
                    "avg_seconds": wait.get("avg_seconds"),
                    "p90_seconds": wait.get("p90_seconds"),
                },
                "sla": analytics.get("sla")
                or {
                    "green": 0,
                    "yellow": 0,
                    "red": 0,
                    "unknown": 0,
                    "target_wait_seconds": 600,
                    "warning_wait_seconds": 900,
                },
            },
            "queues": public_queues,
            "devices": device_health,
            "edge": edge_block,
            "content": content,
            "alerts": alerts,
            "hourly": analytics.get("hourly")
            or [{"hour": h, "issued": 0, "completed": 0} for h in range(24)],
            "sections": sections,
        }

    def _build_queues(self, dept_ids: list[str]) -> list[dict[str, Any]]:
        if not dept_ids:
            return []
        queues = list(
            self.db.scalars(
                select(Queue)
                .options(joinedload(Queue.priority_rule), joinedload(Queue.department))
                .where(Queue.department_id.in_(dept_ids))
                .order_by(Queue.name)
            ).all()
        )
        qs = QueueService(self.db)
        queue_cards: list[dict[str, Any]] = []
        for q in queues:
            st = qs.queue_status(q.id)
            current = st.get("current") or {}
            wait_avg = st.get("estimated_wait_seconds")
            waiting = int(st.get("waiting_count") or 0)
            priority = int(st.get("priority_waiting") or 0)
            status = st.get("status") or "CLOSED"
            sla_level = self._queue_sla_level(waiting, wait_avg, status)
            queue_cards.append(
                {
                    "id": q.id,
                    "name": q.name,
                    "department_name": q.department.name if q.department else None,
                    "status": status,
                    "waiting_count": waiting,
                    "priority_waiting": priority,
                    "current_number": current.get("number"),
                    "current_status": current.get("status"),
                    "estimated_wait_seconds": wait_avg,
                    "sla_level": sla_level,
                    "severity_rank": self._queue_sort_rank(sla_level, status, waiting),
                }
            )
        queue_cards.sort(key=lambda x: (x["severity_rank"], -x["waiting_count"], x["name"]))
        return queue_cards

    def _queue_sla_level(self, waiting: int, wait_seconds: int | None, status: str) -> str:
        if status == "CLOSED":
            return "OK"
        if status == "PAUSED" and waiting > 0:
            return "WARNING"
        wait = wait_seconds or 0
        if waiting >= 15 or wait >= 900:
            return "CRITICAL"
        if waiting >= 8 or wait >= 600:
            return "WARNING"
        return "OK"

    def _queue_sort_rank(self, sla_level: str, status: str, waiting: int) -> int:
        if status == "CLOSED":
            return 50
        if waiting == 0 and status == "OPEN":
            return 40
        return {"CRITICAL": 0, "WARNING": 10, "OK": 20}.get(sla_level, 30)

    def _device_health(
        self,
        devices: list[dict[str, Any]],
        terminals: list[Terminal],
        displays: list[Display],
    ) -> dict[str, Any]:
        def bucket(device_type: str) -> dict[str, Any]:
            rows = [d for d in devices if (d.get("device_type") or "").upper() == device_type]
            online = sum(1 for d in rows if d.get("status") == "ONLINE")
            degraded = sum(1 for d in rows if d.get("status") == "DEGRADED")
            offline = sum(1 for d in rows if d.get("status") == "OFFLINE")
            disabled = sum(1 for d in rows if d.get("status") == "DISABLED")
            level = "OK"
            if offline > 0:
                level = "CRITICAL"
            elif degraded > 0:
                level = "WARNING"
            return {
                "total": len(rows),
                "online": online,
                "degraded": degraded,
                "offline": offline,
                "disabled": disabled,
                "level": level,
                "items": [
                    {
                        "id": d["id"],
                        "name": d["name"],
                        "status": d["status"],
                        "device_type": d["device_type"],
                    }
                    for d in rows
                    if d.get("status") in {"OFFLINE", "DEGRADED"}
                ],
            }

        cats = {
            "DISPLAY": bucket("DISPLAY"),
            "KIOSK": bucket("KIOSK"),
            "PRINTER": bucket("PRINTER"),
            "BUTTON": bucket("BUTTON"),
            "EDGE": bucket("EDGE"),
        }
        if cats["DISPLAY"]["total"] == 0 and displays:
            active = sum(1 for d in displays if d.active)
            cats["DISPLAY"] = {
                "total": len(displays),
                "online": active,
                "degraded": 0,
                "offline": len(displays) - active,
                "disabled": 0,
                "level": "OK" if active == len(displays) else "WARNING",
                "items": [
                    {
                        "id": d.id,
                        "name": d.name,
                        "status": "OFFLINE" if not d.active else "ONLINE",
                        "device_type": "DISPLAY",
                    }
                    for d in displays
                    if not d.active
                ],
            }
        return {
            "categories": cats,
            "terminals": {
                "total": len(terminals),
                "active": sum(1 for t in terminals if t.active),
            },
        }

    def _content_now(self, store_id: str, displays: list[Display]) -> dict[str, Any]:
        active_displays = [d for d in displays if d.active]
        if not active_displays:
            return {"available": False, "message": "Nenhuma tela ativa nesta loja.", "items": []}

        sched = ScheduleService(self.db)
        channels = {c["id"]: c for c in sched.list_channels(store_id=store_id)}
        by_channel: dict[str, dict[str, Any]] = {}
        for d in active_displays:
            if not d.channel_id:
                continue
            ch_id = d.channel_id
            if ch_id not in by_channel:
                try:
                    now = sched.active_at(ch_id)
                except Exception:
                    now = None
                ch_meta = channels.get(ch_id) or {}
                entry: dict[str, Any] = {
                    "channel_id": ch_id,
                    "channel_name": ch_meta.get("name"),
                    "source": now.get("source") if now else None,
                    "playlist_name": None,
                    "schedule_name": None,
                    "priority": None,
                    "screen_count": 0,
                    "screens": [],
                }
                if now and now.get("schedule"):
                    sch = now["schedule"]
                    entry["schedule_name"] = sch.get("name")
                    entry["playlist_name"] = sch.get("playlist_name")
                    entry["priority"] = sch.get("priority")
                elif now and now.get("source") == "channel_default" and ch_meta.get("default_playlist_id"):
                    entry["playlist_name"] = "Playlist padrão do canal"
                by_channel[ch_id] = entry
            by_channel[ch_id]["screen_count"] += 1
            by_channel[ch_id]["screens"].append({"id": d.id, "name": d.name})

        items = list(by_channel.values())
        if not items:
            with_pl = [d for d in active_displays if d.playlist_id]
            if with_pl:
                return {
                    "available": True,
                    "message": None,
                    "items": [
                        {
                            "channel_id": None,
                            "channel_name": None,
                            "playlist_name": "Playlist vinculada à tela",
                            "screen_count": len(with_pl),
                            "screens": [{"id": d.id, "name": d.name} for d in with_pl],
                            "source": "display_playlist",
                        }
                    ],
                }
            return {
                "available": False,
                "message": "Nenhum conteúdo ativo identificado.",
                "items": [],
            }
        return {"available": True, "message": None, "items": items}

    def _derive_alerts(
        self,
        queues: list[dict[str, Any]],
        devices: list[dict[str, Any]],
        edge: dict[str, Any],
        analytics: dict[str, Any],
    ) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []
        for q in queues:
            if q["status"] == "PAUSED" and q["waiting_count"] > 0:
                alerts.append(
                    {
                        "id": f"queue-paused-{q['id']}",
                        "severity": "WARNING",
                        "title": f"{q['name']} pausada com clientes aguardando",
                        "description": f"{q['waiting_count']} na fila.",
                        "href": f"/queues/{q['id']}",
                    }
                )
            if q["sla_level"] == "CRITICAL":
                alerts.append(
                    {
                        "id": f"queue-critical-{q['id']}",
                        "severity": "CRITICAL",
                        "title": f"{q['name']} com espera crítica",
                        "description": (
                            f"{q['waiting_count']} aguardando · estimativa "
                            f"{self._fmt(q.get('estimated_wait_seconds'))}."
                        ),
                        "href": f"/queues/{q['id']}",
                    }
                )
            elif q["sla_level"] == "WARNING" and q["waiting_count"] > 0:
                alerts.append(
                    {
                        "id": f"queue-warn-{q['id']}",
                        "severity": "WARNING",
                        "title": f"{q['name']} exige atenção",
                        "description": f"{q['waiting_count']} aguardando.",
                        "href": f"/queues/{q['id']}",
                    }
                )

        for d in devices:
            st = d.get("status")
            if st == "DISABLED":
                continue
            if st == "OFFLINE":
                alerts.append(
                    {
                        "id": f"device-off-{d['id']}",
                        "severity": "CRITICAL",
                        "title": f"{d['name']} está offline",
                        "description": f"Tipo {d.get('device_type')}.",
                        "href": "/devices",
                    }
                )
            elif st == "DEGRADED":
                alerts.append(
                    {
                        "id": f"device-deg-{d['id']}",
                        "severity": "WARNING",
                        "title": f"{d['name']} degradado",
                        "description": f"Tipo {d.get('device_type')}.",
                        "href": "/devices",
                    }
                )

        if edge.get("status") == "DEGRADED":
            alerts.append(
                {
                    "id": "edge-degraded",
                    "severity": "WARNING",
                    "title": "Edge com pendências ou falhas",
                    "description": f"Pendentes {edge.get('pending', 0)} · falhas {edge.get('failed', 0)}.",
                    "href": "/edge",
                }
            )

        sla = analytics.get("sla") or {}
        if int(sla.get("red") or 0) > 0:
            alerts.append(
                {
                    "id": "sla-red",
                    "severity": "CRITICAL",
                    "title": "Atendimentos com espera crítica hoje",
                    "description": f"{sla.get('red')} senhas acima do limite de SLA.",
                    "href": "/analytics",
                }
            )

        alerts.sort(key=lambda a: (_severity_rank(a["severity"]), a["title"]))
        return alerts

    @staticmethod
    def _fmt(seconds: int | None) -> str:
        if seconds is None:
            return "—"
        m = int(seconds) // 60
        s = int(seconds) % 60
        return f"{m:02d}:{s:02d}"

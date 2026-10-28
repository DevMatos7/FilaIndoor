from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.toledo.models import ToledoDiscovery

MODES = ("NATIVE", "TOLEDO_DISPLAY", "TOLEDO_SYNC", "TOLEDO_FULL")


class ToledoService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def status(self) -> dict[str, Any]:
        from app.modules.toledo.bridge import ToledoBridgeService

        enabled = bool(self.settings.toledo_enabled)
        configured_mode = (self.settings.toledo_mode or "NATIVE").upper()
        if configured_mode not in MODES:
            configured_mode = "NATIVE"
        effective = configured_mode if enabled else "NATIVE"
        bridge = ToledoBridgeService(self.db).describe()
        return {
            "toledo_enabled": enabled,
            "configured_mode": configured_mode,
            "effective_mode": effective,
            "adapter_implemented": True,
            "discovery_only": False,
            "toledo_mock": bool(self.settings.toledo_mock),
            "native": bridge["native"],
            "toledo": bridge["toledo"],
            "message": (
                "Integração Toledo desabilitada — operação NATIVE (adapter em standby)."
                if not enabled
                else f"Toledo ativo em modo {effective}; fila permanece nativa."
            ),
        }

    def get_discovery(self, store_id: str | None = None) -> dict[str, Any]:
        row = self._get_or_create(store_id)
        return self._dict(row)

    def update_discovery(self, data: dict[str, Any], *, store_id: str | None = None, updated_by: str | None = None) -> dict[str, Any]:
        row = self._get_or_create(store_id)
        allowed = {
            "environment_name",
            "mgv_version",
            "mit_version",
            "mit_cloud",
            "mit_cloud_url",
            "license_notes",
            "stores_notes",
            "players_notes",
            "api_enabled",
            "api_base_url",
            "auth_type",
            "integration_key_configured",
            "network_notes",
            "docs_compared",
            "confirmed_capabilities",
            "notes",
            "mode_intent",
        }
        for key, value in data.items():
            if key not in allowed:
                continue
            if key == "mode_intent" and value and str(value).upper() not in MODES:
                continue
            if key == "mode_intent" and value:
                value = str(value).upper()
            setattr(row, key, value)
        if updated_by:
            row.updated_by = updated_by
        self.db.commit()
        self.db.refresh(row)
        return self._dict(row)

    def completeness(self, store_id: str | None = None) -> dict[str, Any]:
        row = self._get_or_create(store_id)
        checks = {
            "mgv_version": bool(row.mgv_version),
            "mit_version": bool(row.mit_version),
            "mit_cloud": row.mit_cloud is not None,
            "api_enabled": row.api_enabled is not None,
            "api_base_url": bool(row.api_base_url) if row.api_enabled else True,
            "players_notes": bool(row.players_notes),
            "docs_compared": bool(row.docs_compared),
        }
        done = sum(1 for v in checks.values() if v)
        return {
            "fields": checks,
            "completed": done,
            "total": len(checks),
            "percent": round(100 * done / len(checks)),
            "ready_for_sprint14": done == len(checks) and bool(self.settings.toledo_enabled) is False,
        }

    def _get_or_create(self, store_id: str | None) -> ToledoDiscovery:
        stmt = select(ToledoDiscovery)
        if store_id:
            stmt = stmt.where(ToledoDiscovery.store_id == store_id)
        else:
            stmt = stmt.where(ToledoDiscovery.store_id.is_(None))
        row = self.db.scalar(stmt.order_by(ToledoDiscovery.created_at.asc()))
        if row:
            return row
        row = ToledoDiscovery(store_id=store_id, environment_name="default", mode_intent="NATIVE")
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def _dict(self, row: ToledoDiscovery) -> dict[str, Any]:
        return {
            "id": row.id,
            "store_id": row.store_id,
            "environment_name": row.environment_name,
            "mgv_version": row.mgv_version,
            "mit_version": row.mit_version,
            "mit_cloud": row.mit_cloud,
            "mit_cloud_url": row.mit_cloud_url,
            "license_notes": row.license_notes,
            "stores_notes": row.stores_notes,
            "players_notes": row.players_notes,
            "api_enabled": row.api_enabled,
            "api_base_url": row.api_base_url,
            "auth_type": row.auth_type,
            "integration_key_configured": row.integration_key_configured,
            "network_notes": row.network_notes,
            "docs_compared": row.docs_compared,
            "confirmed_capabilities": row.confirmed_capabilities or {},
            "notes": row.notes,
            "mode_intent": row.mode_intent,
            "updated_by": row.updated_by,
            "updated_at": row.updated_at.isoformat() + "Z" if row.updated_at else None,
        }

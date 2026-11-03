"""Layout Engine (UX-6B) — templates, zones, resolution, legacy mapping."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.signage.models import Channel, LayoutTemplate, LayoutZone
from app.modules.queue.models.entities import utcnow

# Legacy Channel.layout → system slug (audit: only queue_media_split found in codebase/defaults)
LEGACY_LAYOUT_MAP: dict[str, str] = {
    "queue_media_split": "media_queue_footer",
}

DEFAULT_SLUG = "media_queue_footer"

ZONE_TYPES = {"MEDIA", "QUEUE", "TEXT", "CLOCK", "TICKER"}

# Deterministic system IDs (idempotent seed)
SYS = {
    "fullscreen_media": {
        "id": "sys-tpl-fullscreen-media",
        "name": "Mídia tela cheia",
        "slug": "fullscreen_media",
        "zones": [
            {
                "id": "sys-zone-fs-media",
                "name": "Mídia",
                "zone_type": "MEDIA",
                "x": 0,
                "y": 0,
                "width": 100,
                "height": 100,
                "z_index": 0,
                "config": {},
            }
        ],
    },
    "media_queue_footer": {
        "id": "sys-tpl-media-queue-footer",
        "name": "Mídia + fila inferior",
        "slug": "media_queue_footer",
        "zones": [
            {
                "id": "sys-zone-mqf-media",
                "name": "Mídia",
                "zone_type": "MEDIA",
                "x": 0,
                "y": 0,
                "width": 100,
                "height": 82,
                "z_index": 0,
                "config": {},
            },
            {
                "id": "sys-zone-mqf-queue",
                "name": "Fila",
                "zone_type": "QUEUE",
                "x": 0,
                "y": 82,
                "width": 100,
                "height": 18,
                "z_index": 1,
                "config": {"variant": "footer", "show_last_called": True, "show_label": True},
            },
        ],
    },
    "media_queue_sidebar": {
        "id": "sys-tpl-media-queue-sidebar",
        "name": "Mídia + fila lateral",
        "slug": "media_queue_sidebar",
        "zones": [
            {
                "id": "sys-zone-mqs-media",
                "name": "Mídia",
                "zone_type": "MEDIA",
                "x": 0,
                "y": 0,
                "width": 72,
                "height": 100,
                "z_index": 0,
                "config": {},
            },
            {
                "id": "sys-zone-mqs-queue",
                "name": "Fila",
                "zone_type": "QUEUE",
                "x": 72,
                "y": 0,
                "width": 28,
                "height": 100,
                "z_index": 1,
                "config": {"variant": "sidebar", "show_last_called": True, "show_label": True},
            },
        ],
    },
    "queue_fullscreen": {
        "id": "sys-tpl-queue-fullscreen",
        "name": "Fila tela cheia",
        "slug": "queue_fullscreen",
        "zones": [
            {
                "id": "sys-zone-qf-queue",
                "name": "Fila",
                "zone_type": "QUEUE",
                "x": 0,
                "y": 0,
                "width": 100,
                "height": 100,
                "z_index": 0,
                "config": {"variant": "fullscreen", "show_last_called": True, "show_label": True},
            }
        ],
    },
}


def _dec(v: float | int | Decimal) -> Decimal:
    return Decimal(str(v))


def validate_zone_geometry(*, x: Decimal, y: Decimal, width: Decimal, height: Decimal) -> None:
    if x < 0 or y < 0:
        raise ValidationError("Zona: x/y devem ser >= 0")
    if width <= 0 or height <= 0:
        raise ValidationError("Zona: width/height devem ser > 0")
    if x + width > Decimal("100") or y + height > Decimal("100"):
        raise ValidationError("Zona: x+width e y+height devem ser <= 100")


def zone_to_dict(z: LayoutZone) -> dict[str, Any]:
    return {
        "id": z.id,
        "name": z.name,
        "type": z.zone_type,
        "x": float(z.x),
        "y": float(z.y),
        "width": float(z.width),
        "height": float(z.height),
        "z_index": z.z_index,
        "config": z.config or {},
    }


def template_to_dict(t: LayoutTemplate, *, include_zones: bool = True) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": t.id,
        "store_id": t.store_id,
        "name": t.name,
        "slug": t.slug,
        "orientation": t.orientation,
        "aspect_ratio": t.aspect_ratio,
        "background": t.background or {"type": "color", "value": "#071a12"},
        "config": t.config or {"safe_area": 3},
        "active": t.active,
        "is_system": t.is_system,
    }
    if include_zones:
        zones = sorted(t.zones or [], key=lambda z: (z.z_index, z.name))
        # Preferência MVP: no máximo uma MEDIA zone
        media_seen = False
        filtered: list[dict[str, Any]] = []
        for z in zones:
            if z.zone_type == "MEDIA":
                if media_seen:
                    continue
                media_seen = True
            filtered.append(zone_to_dict(z))
        payload["zones"] = filtered
    return payload


class LayoutService:
    def __init__(self, db: Session):
        self.db = db

    def ensure_system_templates(self) -> None:
        """Idempotent seed — safe for fresh DB and upgrades (also used by SQLite tests)."""
        for meta in SYS.values():
            existing = self.db.get(LayoutTemplate, meta["id"])
            if existing:
                continue
            # Avoid duplicate by slug (global)
            by_slug = self.db.scalar(
                select(LayoutTemplate).where(
                    LayoutTemplate.store_id.is_(None),
                    LayoutTemplate.slug == meta["slug"],
                )
            )
            if by_slug:
                continue
            tpl = LayoutTemplate(
                id=meta["id"],
                store_id=None,
                name=meta["name"],
                slug=meta["slug"],
                orientation="LANDSCAPE",
                aspect_ratio="16:9",
                background={"type": "color", "value": "#071a12"},
                config={"safe_area": 3},
                active=True,
                is_system=True,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            self.db.add(tpl)
            self.db.flush()
            for z in meta["zones"]:
                validate_zone_geometry(
                    x=_dec(z["x"]), y=_dec(z["y"]), width=_dec(z["width"]), height=_dec(z["height"])
                )
                self.db.add(
                    LayoutZone(
                        id=z["id"],
                        layout_template_id=tpl.id,
                        name=z["name"],
                        zone_type=z["zone_type"],
                        x=_dec(z["x"]),
                        y=_dec(z["y"]),
                        width=_dec(z["width"]),
                        height=_dec(z["height"]),
                        z_index=int(z["z_index"]),
                        config=z.get("config") or {},
                    )
                )
        self.db.commit()

    def list_templates(self, store_id: str | None = None) -> list[dict[str, Any]]:
        self.ensure_system_templates()
        stmt = (
            select(LayoutTemplate)
            .options(joinedload(LayoutTemplate.zones))
            .where(LayoutTemplate.active.is_(True))
            .order_by(LayoutTemplate.is_system.desc(), LayoutTemplate.name)
        )
        rows = list(self.db.scalars(stmt).unique().all())
        if store_id:
            rows = [t for t in rows if t.store_id is None or t.store_id == store_id]
        else:
            # sem filtro: system + todos store (admin overview)
            pass
        return [template_to_dict(t) for t in rows]

    def get_template(self, template_id: str) -> dict[str, Any]:
        self.ensure_system_templates()
        t = self.db.scalar(
            select(LayoutTemplate)
            .options(joinedload(LayoutTemplate.zones))
            .where(LayoutTemplate.id == template_id)
        )
        if not t:
            raise NotFoundError("Layout template não encontrado")
        return template_to_dict(t)

    def get_by_slug(self, slug: str, *, store_id: str | None = None) -> LayoutTemplate | None:
        if store_id:
            store_tpl = self.db.scalar(
                select(LayoutTemplate)
                .options(joinedload(LayoutTemplate.zones))
                .where(
                    LayoutTemplate.store_id == store_id,
                    LayoutTemplate.slug == slug,
                    LayoutTemplate.active.is_(True),
                )
            )
            if store_tpl:
                return store_tpl
        return self.db.scalar(
            select(LayoutTemplate)
            .options(joinedload(LayoutTemplate.zones))
            .where(
                LayoutTemplate.store_id.is_(None),
                LayoutTemplate.slug == slug,
                LayoutTemplate.active.is_(True),
            )
        )

    def resolve_for_channel(
        self,
        *,
        channel: Channel | None,
        store_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Resolution order:
        1. channel.layout_template_id (active)
        2. legacy channel.layout → system slug map
        3. media_queue_footer system
        """
        self.ensure_system_templates()
        store = store_id or (channel.store_id if channel else None)

        if channel and channel.layout_template_id:
            tpl = self.db.scalar(
                select(LayoutTemplate)
                .options(joinedload(LayoutTemplate.zones))
                .where(
                    LayoutTemplate.id == channel.layout_template_id,
                    LayoutTemplate.active.is_(True),
                )
            )
            if tpl:
                return {**template_to_dict(tpl), "resolved_from": "layout_template_id"}

        if channel and channel.layout:
            slug = LEGACY_LAYOUT_MAP.get(channel.layout)
            if slug:
                mapped = self.get_by_slug(slug, store_id=store)
                if mapped:
                    return {**template_to_dict(mapped), "resolved_from": "legacy_layout", "legacy_layout": channel.layout}
            # Unknown legacy value — document via resolved_from, still fall through
            if channel.layout not in LEGACY_LAYOUT_MAP:
                # try treating layout string itself as slug
                as_slug = self.get_by_slug(channel.layout, store_id=store)
                if as_slug:
                    return {
                        **template_to_dict(as_slug),
                        "resolved_from": "legacy_layout_as_slug",
                        "legacy_layout": channel.layout,
                    }

        fallback = self.get_by_slug(DEFAULT_SLUG, store_id=store)
        if fallback:
            return {**template_to_dict(fallback), "resolved_from": "default"}

        # Emergency hard-coded payload (should not happen after ensure)
        return {
            "id": "emergency-media-queue-footer",
            "store_id": None,
            "name": "Mídia + fila inferior",
            "slug": DEFAULT_SLUG,
            "orientation": "LANDSCAPE",
            "aspect_ratio": "16:9",
            "background": {"type": "color", "value": "#071a12"},
            "config": {"safe_area": 3},
            "active": True,
            "is_system": True,
            "resolved_from": "emergency",
            "zones": [
                {
                    "id": "emergency-media",
                    "name": "Mídia",
                    "type": "MEDIA",
                    "x": 0,
                    "y": 0,
                    "width": 100,
                    "height": 82,
                    "z_index": 0,
                    "config": {},
                },
                {
                    "id": "emergency-queue",
                    "name": "Fila",
                    "type": "QUEUE",
                    "x": 0,
                    "y": 82,
                    "width": 100,
                    "height": 18,
                    "z_index": 1,
                    "config": {"variant": "footer", "show_last_called": True, "show_label": True},
                },
            ],
        }

    def resolve_for_display(self, *, channel_id: str | None, store_id: str | None) -> dict[str, Any]:
        channel = None
        if channel_id:
            channel = self.db.get(Channel, channel_id)
        return self.resolve_for_channel(channel=channel, store_id=store_id)

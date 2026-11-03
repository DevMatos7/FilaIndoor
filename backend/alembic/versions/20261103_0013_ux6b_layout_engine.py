"""UX-6B — Layout Engine (layout_templates, layout_zones, channel.layout_template_id)

Revision ID: 20261103_0013
Revises: 20261028_0012
Create Date: 2026-11-03

Tables:
- layout_templates (system + store-scoped)
- layout_zones (percent geometry 0–100)

Channel:
- layout_template_id nullable FK (ON DELETE SET NULL)
- legacy layout string PRESERVED

Indexes:
- partial unique slug WHERE store_id IS NULL
- uq_layout_templates_store_slug (store_id, slug)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision: str = "20261103_0013"
down_revision: Union[str, None] = "20261028_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SYSTEM_TEMPLATES = [
    {
        "id": "sys-tpl-fullscreen-media",
        "name": "Mídia tela cheia",
        "slug": "fullscreen_media",
        "zones": [
            ("sys-zone-fs-media", "Mídia", "MEDIA", 0, 0, 100, 100, 0, '{"type":"media"}'),
        ],
    },
    {
        "id": "sys-tpl-media-queue-footer",
        "name": "Mídia + fila inferior",
        "slug": "media_queue_footer",
        "zones": [
            ("sys-zone-mqf-media", "Mídia", "MEDIA", 0, 0, 100, 82, 0, "{}"),
            (
                "sys-zone-mqf-queue",
                "Fila",
                "QUEUE",
                0,
                82,
                100,
                18,
                1,
                '{"variant":"footer","show_last_called":true,"show_label":true}',
            ),
        ],
    },
    {
        "id": "sys-tpl-media-queue-sidebar",
        "name": "Mídia + fila lateral",
        "slug": "media_queue_sidebar",
        "zones": [
            ("sys-zone-mqs-media", "Mídia", "MEDIA", 0, 0, 72, 100, 0, "{}"),
            (
                "sys-zone-mqs-queue",
                "Fila",
                "QUEUE",
                72,
                0,
                28,
                100,
                1,
                '{"variant":"sidebar","show_last_called":true,"show_label":true}',
            ),
        ],
    },
    {
        "id": "sys-tpl-queue-fullscreen",
        "name": "Fila tela cheia",
        "slug": "queue_fullscreen",
        "zones": [
            (
                "sys-zone-qf-queue",
                "Fila",
                "QUEUE",
                0,
                0,
                100,
                100,
                0,
                '{"variant":"fullscreen","show_last_called":true,"show_label":true}',
            ),
        ],
    },
]


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())

    if "layout_templates" not in tables:
        op.create_table(
            "layout_templates",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=True),
            sa.Column("name", sa.String(180), nullable=False),
            sa.Column("slug", sa.String(80), nullable=False),
            sa.Column("orientation", sa.String(20), nullable=False, server_default="LANDSCAPE"),
            sa.Column("aspect_ratio", sa.String(20), nullable=False, server_default="16:9"),
            sa.Column("background", sa.JSON(), nullable=True),
            sa.Column("config", sa.JSON(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("store_id", "slug", name="uq_layout_templates_store_slug"),
        )
        op.create_index("ix_layout_templates_store_id", "layout_templates", ["store_id"])
        op.create_index("ix_layout_templates_slug", "layout_templates", ["slug"])
        # Global slug uniqueness (store_id IS NULL)
        op.create_index(
            "uq_layout_templates_global_slug",
            "layout_templates",
            ["slug"],
            unique=True,
            postgresql_where=sa.text("store_id IS NULL"),
            sqlite_where=sa.text("store_id IS NULL"),
        )

    if "layout_zones" not in tables:
        op.create_table(
            "layout_zones",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "layout_template_id",
                sa.String(36),
                sa.ForeignKey("layout_templates.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("zone_type", sa.String(40), nullable=False),
            sa.Column("x", sa.Numeric(5, 2), nullable=False, server_default="0"),
            sa.Column("y", sa.Numeric(5, 2), nullable=False, server_default="0"),
            sa.Column("width", sa.Numeric(5, 2), nullable=False, server_default="100"),
            sa.Column("height", sa.Numeric(5, 2), nullable=False, server_default="100"),
            sa.Column("z_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("config", sa.JSON(), nullable=True),
        )
        op.create_index("ix_layout_zones_layout_template_id", "layout_zones", ["layout_template_id"])

    cols = {c["name"] for c in inspect(bind).get_columns("channels")} if "channels" in tables else set()
    if "channels" in tables and "layout_template_id" not in cols:
        op.add_column(
            "channels",
            sa.Column(
                "layout_template_id",
                sa.String(36),
                sa.ForeignKey("layout_templates.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index("ix_channels_layout_template_id", "channels", ["layout_template_id"])

    # Seed system templates idempotently (dialect-safe via SQLAlchemy Core)
    import json
    from datetime import datetime

    now = datetime.utcnow()
    lt = sa.table(
        "layout_templates",
        sa.column("id", sa.String),
        sa.column("store_id", sa.String),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("orientation", sa.String),
        sa.column("aspect_ratio", sa.String),
        sa.column("background", sa.JSON),
        sa.column("config", sa.JSON),
        sa.column("active", sa.Boolean),
        sa.column("is_system", sa.Boolean),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    lz = sa.table(
        "layout_zones",
        sa.column("id", sa.String),
        sa.column("layout_template_id", sa.String),
        sa.column("name", sa.String),
        sa.column("zone_type", sa.String),
        sa.column("x", sa.Numeric),
        sa.column("y", sa.Numeric),
        sa.column("width", sa.Numeric),
        sa.column("height", sa.Numeric),
        sa.column("z_index", sa.Integer),
        sa.column("config", sa.JSON),
    )
    for tpl in SYSTEM_TEMPLATES:
        exists = bind.execute(
            text("SELECT 1 FROM layout_templates WHERE id = :id"),
            {"id": tpl["id"]},
        ).first()
        if exists:
            continue
        slug_exists = bind.execute(
            text("SELECT 1 FROM layout_templates WHERE store_id IS NULL AND slug = :slug"),
            {"slug": tpl["slug"]},
        ).first()
        if slug_exists:
            continue
        bind.execute(
            lt.insert().values(
                id=tpl["id"],
                store_id=None,
                name=tpl["name"],
                slug=tpl["slug"],
                orientation="LANDSCAPE",
                aspect_ratio="16:9",
                background={"type": "color", "value": "#071a12"},
                config={"safe_area": 3},
                active=True,
                is_system=True,
                created_at=now,
                updated_at=now,
            )
        )
        for z in tpl["zones"]:
            zid, zname, ztype, x, y, w, h, zi, cfg = z
            bind.execute(
                lz.insert().values(
                    id=zid,
                    layout_template_id=tpl["id"],
                    name=zname,
                    zone_type=ztype,
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                    z_index=zi,
                    config=json.loads(cfg) if isinstance(cfg, str) else cfg,
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "channels" in tables:
        cols = {c["name"] for c in inspect(bind).get_columns("channels")}
        if "layout_template_id" in cols:
            op.drop_index("ix_channels_layout_template_id", table_name="channels")
            op.drop_column("channels", "layout_template_id")
    # Do not cascade-delete channel data; only drop new tables
    if "layout_zones" in tables:
        op.drop_table("layout_zones")
    if "layout_templates" in tables:
        op.drop_table("layout_templates")

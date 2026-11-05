"""DRC-2 — Price Table Engine (dynamic content)

Revision ID: 20261105_0016
Revises: 20261105_0015
Create Date: 2026-11-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision: str = "20261105_0016"
down_revision: Union[str, None] = "20261105_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SYSTEM_TEMPLATES = [
    (
        "sys-dct-price-table-clean",
        "Tabela limpa",
        "price_table_clean",
        '{"ui_name":"Tabela limpa","default_items_per_page":8,"min_items_per_page":4,"max_items_per_page":12,"row_density":"comfortable","show_unit":true,"show_regular_price":true,"show_promo_badge":true,"show_header":true,"columns":1}',
    ),
    (
        "sys-dct-price-table-compact",
        "Tabela compacta",
        "price_table_compact",
        '{"ui_name":"Tabela compacta","default_items_per_page":16,"min_items_per_page":8,"max_items_per_page":24,"row_density":"compact","show_unit":true,"show_regular_price":false,"show_promo_badge":true,"show_header":true,"columns":1}',
    ),
    (
        "sys-dct-price-table-two-columns",
        "Tabela duas colunas",
        "price_table_two_columns",
        '{"ui_name":"Tabela duas colunas","default_items_per_page":12,"min_items_per_page":6,"max_items_per_page":20,"row_density":"comfortable","show_unit":true,"show_regular_price":true,"show_promo_badge":true,"show_header":true,"columns":2}',
    ),
    (
        "sys-dct-price-table-promo",
        "Tabela promocional",
        "price_table_promo",
        '{"ui_name":"Tabela promocional","default_items_per_page":6,"min_items_per_page":3,"max_items_per_page":10,"row_density":"emphasis","show_unit":true,"show_regular_price":true,"show_promo_badge":true,"show_header":true,"columns":1,"emphasize_promo":true}',
    ),
]


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())

    if "dynamic_content_templates" not in tables:
        op.create_table(
            "dynamic_content_templates",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("slug", sa.String(80), nullable=False),
            sa.Column("content_type", sa.String(40), nullable=False, server_default="PRICE_TABLE"),
            sa.Column("orientation", sa.String(20), nullable=False, server_default="landscape"),
            sa.Column("aspect_ratio", sa.String(20), nullable=False, server_default="16:9"),
            sa.Column("config", sa.JSON(), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("store_id", "slug", name="uq_dynamic_content_templates_store_slug"),
        )
        op.create_index("ix_dynamic_content_templates_store_id", "dynamic_content_templates", ["store_id"])
        dialect = bind.dialect.name
        if dialect == "postgresql":
            op.execute(
                text(
                    "CREATE UNIQUE INDEX uq_dynamic_content_templates_global_slug "
                    "ON dynamic_content_templates (slug) WHERE store_id IS NULL"
                )
            )
        else:
            op.execute(
                text(
                    "CREATE UNIQUE INDEX uq_dynamic_content_templates_global_slug "
                    "ON dynamic_content_templates (slug) WHERE store_id IS NULL"
                )
            )

    if "dynamic_contents" not in tables:
        op.create_table(
            "dynamic_contents",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("description", sa.String(500), nullable=True),
            sa.Column("content_type", sa.String(40), nullable=False, server_default="PRICE_TABLE"),
            sa.Column("selection_mode", sa.String(20), nullable=False),
            sa.Column(
                "template_id",
                sa.String(36),
                sa.ForeignKey("dynamic_content_templates.id"),
                nullable=False,
            ),
            sa.Column("config", sa.JSON(), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_dynamic_contents_store_id", "dynamic_contents", ["store_id"])

    if "dynamic_content_rules" not in tables:
        op.create_table(
            "dynamic_content_rules",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "dynamic_content_id",
                sa.String(36),
                sa.ForeignKey("dynamic_contents.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("section_code", sa.String(40), nullable=True),
            sa.Column("group_code", sa.String(40), nullable=True),
            sa.Column("subgroup_code", sa.String(40), nullable=True),
            sa.Column("promotion_only", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("available_only", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("limit_items", sa.Integer(), nullable=True),
            sa.Column("sort_mode", sa.String(40), nullable=False, server_default="NAME_ASC"),
            sa.Column("config", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_dynamic_content_rules_content_id", "dynamic_content_rules", ["dynamic_content_id"])

    if "dynamic_content_products" not in tables:
        op.create_table(
            "dynamic_content_products",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "dynamic_content_id",
                sa.String(36),
                sa.ForeignKey("dynamic_contents.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "product_id",
                sa.String(36),
                sa.ForeignKey("retail_products.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("position", sa.Integer(), nullable=True),
            sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("excluded", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("dynamic_content_id", "product_id", name="uq_dynamic_content_product"),
        )
        op.create_index("ix_dynamic_content_products_content_id", "dynamic_content_products", ["dynamic_content_id"])

    if "dynamic_render_snapshots" not in tables:
        op.create_table(
            "dynamic_render_snapshots",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "dynamic_content_id",
                sa.String(36),
                sa.ForeignKey("dynamic_contents.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
            sa.Column("content_hash", sa.String(64), nullable=False),
            sa.Column("data_version", sa.String(80), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("item_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("page_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("source_freshness", sa.String(20), nullable=False),
            sa.Column("generated_at", sa.DateTime(), nullable=False),
            sa.Column("valid_until", sa.DateTime(), nullable=True),
            sa.Column("publishable", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("warnings", sa.JSON(), nullable=False),
        )
        op.create_index("ix_dynamic_render_snapshots_content_id", "dynamic_render_snapshots", ["dynamic_content_id"])
        op.create_index("ix_dynamic_render_snapshots_store_id", "dynamic_render_snapshots", ["store_id"])

    # idempotent system seed
    import json
    from datetime import datetime

    conn = op.get_bind()
    now = datetime.utcnow()
    for tid, name, slug, cfg in SYSTEM_TEMPLATES:
        exists = conn.execute(
            text("SELECT 1 FROM dynamic_content_templates WHERE id = :id OR (store_id IS NULL AND slug = :slug)"),
            {"id": tid, "slug": slug},
        ).fetchone()
        if exists:
            continue
        conn.execute(
            text(
                "INSERT INTO dynamic_content_templates "
                "(id, store_id, name, slug, content_type, orientation, aspect_ratio, config, active, is_system, created_at, updated_at) "
                + (
                    "VALUES (:id, NULL, :name, :slug, 'PRICE_TABLE', 'landscape', '16:9', CAST(:cfg AS JSON), :active, :is_system, :created_at, :updated_at)"
                    if bind.dialect.name != "sqlite"
                    else "VALUES (:id, NULL, :name, :slug, 'PRICE_TABLE', 'landscape', '16:9', :cfg, :active, :is_system, :created_at, :updated_at)"
                )
            ),
            {
                "id": tid,
                "name": name,
                "slug": slug,
                "cfg": cfg,
                "active": True,
                "is_system": True,
                "created_at": now,
                "updated_at": now,
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    for t in (
        "dynamic_render_snapshots",
        "dynamic_content_products",
        "dynamic_content_rules",
        "dynamic_contents",
        "dynamic_content_templates",
    ):
        if t in tables:
            op.drop_table(t)

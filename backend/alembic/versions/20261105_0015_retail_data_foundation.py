"""DRC-1 — Retail Data Foundation

Revision ID: 20261105_0015
Revises: 20261104_0014
Create Date: 2026-11-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20261105_0015"
down_revision: Union[str, None] = "20261104_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())

    if "retail_store_sources" not in tables:
        op.create_table(
            "retail_store_sources",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
            sa.Column("source_system", sa.String(40), nullable=False, server_default="CISS"),
            sa.Column("company_code", sa.String(40), nullable=False),
            sa.Column("location_code", sa.String(40), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("store_id", "source_system", name="uq_retail_store_source_store_sys"),
            sa.UniqueConstraint("source_system", "company_code", name="uq_retail_store_source_sys_company"),
        )
        op.create_index("ix_retail_store_sources_store_id", "retail_store_sources", ["store_id"])

    if "retail_products" not in tables:
        op.create_table(
            "retail_products",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("source_system", sa.String(40), nullable=False, server_default="CISS"),
            sa.Column("source_product_id", sa.String(80), nullable=False),
            sa.Column("gtin", sa.String(32), nullable=True),
            sa.Column("description", sa.String(255), nullable=False),
            sa.Column("commercial_description", sa.String(255), nullable=True),
            sa.Column("unit", sa.String(20), nullable=True),
            sa.Column("section_code", sa.String(40), nullable=True),
            sa.Column("section_name", sa.String(120), nullable=True),
            sa.Column("group_code", sa.String(40), nullable=True),
            sa.Column("group_name", sa.String(120), nullable=True),
            sa.Column("subgroup_code", sa.String(40), nullable=True),
            sa.Column("subgroup_name", sa.String(120), nullable=True),
            sa.Column("brand", sa.String(120), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("source_updated_at", sa.DateTime(), nullable=True),
            sa.Column("synced_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("source_system", "source_product_id", name="uq_retail_product_source"),
        )
        op.create_index("ix_retail_products_gtin", "retail_products", ["gtin"])
        op.create_index("ix_retail_products_section", "retail_products", ["section_code"])

    if "retail_store_products" not in tables:
        op.create_table(
            "retail_store_products",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
            sa.Column("product_id", sa.String(36), sa.ForeignKey("retail_products.id", ondelete="CASCADE"), nullable=False),
            sa.Column("source_company_code", sa.String(40), nullable=False),
            sa.Column("sellable", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("available", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("current_stock_qty", sa.Float(), nullable=True),
            sa.Column("source_hash", sa.String(64), nullable=True),
            sa.Column("source_updated_at", sa.DateTime(), nullable=True),
            sa.Column("synced_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("store_id", "product_id", name="uq_retail_store_product"),
        )
        op.create_index("ix_retail_store_products_store", "retail_store_products", ["store_id"])

    if "retail_prices" not in tables:
        op.create_table(
            "retail_prices",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
            sa.Column("product_id", sa.String(36), sa.ForeignKey("retail_products.id", ondelete="CASCADE"), nullable=False),
            sa.Column("price_kind", sa.String(20), nullable=False),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("min_qty", sa.Float(), nullable=True),
            sa.Column("max_qty", sa.Float(), nullable=True),
            sa.Column("unit", sa.String(20), nullable=True),
            sa.Column("starts_at", sa.DateTime(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("source_ref", sa.String(120), nullable=True),
            sa.Column("condition_text", sa.String(255), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("source_updated_at", sa.DateTime(), nullable=True),
            sa.Column("synced_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_retail_prices_store_product", "retail_prices", ["store_id", "product_id"])
        op.create_index("ix_retail_prices_kind", "retail_prices", ["price_kind"])

    if "retail_promotions" not in tables:
        op.create_table(
            "retail_promotions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
            sa.Column("product_id", sa.String(36), sa.ForeignKey("retail_products.id", ondelete="CASCADE"), nullable=False),
            sa.Column("source_promotion_id", sa.String(80), nullable=True),
            sa.Column("promotion_type", sa.String(40), nullable=False, server_default="NORMAL"),
            sa.Column("promo_amount", sa.Float(), nullable=False),
            sa.Column("starts_at", sa.DateTime(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("condition_text", sa.String(255), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("source_updated_at", sa.DateTime(), nullable=True),
            sa.Column("synced_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_retail_promotions_store_product", "retail_promotions", ["store_id", "product_id"])

    if "retail_sync_watermarks" not in tables:
        op.create_table(
            "retail_sync_watermarks",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("source_system", sa.String(40), nullable=False, server_default="CISS"),
            sa.Column("entity", sa.String(40), nullable=False),
            sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=True),
            sa.Column("watermark_value", sa.String(120), nullable=True),
            sa.Column("last_success_at", sa.DateTime(), nullable=True),
            sa.Column("last_error_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("source_system", "entity", "store_id", name="uq_retail_sync_watermark"),
        )

    if "retail_sync_runs" not in tables:
        op.create_table(
            "retail_sync_runs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("source_system", sa.String(40), nullable=False, server_default="CISS"),
            sa.Column("entity", sa.String(40), nullable=False),
            sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id", ondelete="SET NULL"), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="RUNNING"),
            sa.Column("records_read", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("records_inserted", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("records_updated", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("records_skipped", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("records_failed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("watermark_before", sa.String(120), nullable=True),
            sa.Column("watermark_after", sa.String(120), nullable=True),
            sa.Column("error_summary", sa.Text(), nullable=True),
        )
        op.create_index("ix_retail_sync_runs_store", "retail_sync_runs", ["store_id"])
        op.create_index("ix_retail_sync_runs_started", "retail_sync_runs", ["started_at"])


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    for name in (
        "retail_sync_runs",
        "retail_sync_watermarks",
        "retail_promotions",
        "retail_prices",
        "retail_store_products",
        "retail_products",
        "retail_store_sources",
    ):
        if name in tables:
            op.drop_table(name)

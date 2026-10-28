"""Sprint 12 — ERP/CISS integration + snapshots + offer templates

Revision ID: 20261028_0010
Revises: 20261027_0009
Create Date: 2026-10-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20261028_0010"
down_revision: Union[str, None] = "20261027_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())

    if "integrations" not in tables:
        op.create_table(
            "integrations",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id", ondelete="SET NULL"), nullable=True),
            sa.Column("provider", sa.String(40), nullable=False, server_default="mock"),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("external_store_id", sa.String(80), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("config", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_integrations_store_id", "integrations", ["store_id"])

    if "integration_sync_runs" not in tables:
        op.create_table(
            "integration_sync_runs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("integration_id", sa.String(36), nullable=True),
            sa.Column("provider", sa.String(40), nullable=False),
            sa.Column("store_id", sa.String(36), nullable=True),
            sa.Column("sync_type", sa.String(40), nullable=False, server_default="FULL"),
            sa.Column("status", sa.String(20), nullable=False, server_default="RUNNING"),
            sa.Column("products_upserted", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("snapshots_upserted", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_integration_sync_runs_integration_id", "integration_sync_runs", ["integration_id"])
        op.create_index("ix_integration_sync_runs_store_id", "integration_sync_runs", ["store_id"])
        op.create_index("ix_integration_sync_runs_started", "integration_sync_runs", ["started_at"])

    if "erp_products" not in tables:
        op.create_table(
            "erp_products",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("provider", sa.String(40), nullable=False, server_default="mock"),
            sa.Column("external_product_id", sa.String(80), nullable=False),
            sa.Column("sku", sa.String(80), nullable=True),
            sa.Column("ean", sa.String(32), nullable=True),
            sa.Column("description", sa.String(255), nullable=False),
            sa.Column("unit", sa.String(20), nullable=True),
            sa.Column("section_code", sa.String(40), nullable=True),
            sa.Column("group_code", sa.String(40), nullable=True),
            sa.Column("subgroup_code", sa.String(40), nullable=True),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column("synced_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("provider", "external_product_id", name="uq_erp_product_provider_ext"),
        )
        op.create_index("ix_erp_products_sku", "erp_products", ["sku"])
        op.create_index("ix_erp_products_ean", "erp_products", ["ean"])

    if "erp_product_store_snapshots" not in tables:
        op.create_table(
            "erp_product_store_snapshots",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("product_id", sa.String(36), sa.ForeignKey("erp_products.id", ondelete="CASCADE"), nullable=False),
            sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
            sa.Column("regular_price", sa.Float(), nullable=True),
            sa.Column("promo_price", sa.Float(), nullable=True),
            sa.Column("promo_start", sa.DateTime(), nullable=True),
            sa.Column("promo_end", sa.DateTime(), nullable=True),
            sa.Column("stock_qty", sa.Float(), nullable=True),
            sa.Column("synced_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("product_id", "store_id", name="uq_erp_snapshot_product_store"),
        )
        op.create_index("ix_erp_product_store_snapshots_product_id", "erp_product_store_snapshots", ["product_id"])
        op.create_index("ix_erp_snapshots_store", "erp_product_store_snapshots", ["store_id"])

    if "product_offer_templates" not in tables:
        op.create_table(
            "product_offer_templates",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(180), nullable=False),
            sa.Column("product_external_id", sa.String(80), nullable=False),
            sa.Column("template_key", sa.String(60), nullable=False, server_default="oferta_acougue"),
            sa.Column("only_in_stock", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("min_stock_qty", sa.Float(), nullable=False, server_default="0.01"),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_product_offer_templates_store_id", "product_offer_templates", ["store_id"])
        op.create_index("ix_product_offer_templates_product_external_id", "product_offer_templates", ["product_external_id"])


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    for name in (
        "product_offer_templates",
        "erp_product_store_snapshots",
        "erp_products",
        "integration_sync_runs",
        "integrations",
    ):
        if name in tables:
            op.drop_table(name)

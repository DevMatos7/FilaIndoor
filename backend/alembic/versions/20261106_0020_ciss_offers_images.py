"""DRC-5R — RetailOfferCampaign/Item + PriceChain

Revision ID: 20261106_0020
Revises: 20261106_0019
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20261106_0020"
down_revision: Union[str, None] = "20261106_0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())

    if "retail_price_chains" not in tables:
        op.create_table(
            "retail_price_chains",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("source_system", sa.String(40), nullable=False, server_default="CISS"),
            sa.Column("source_chain_id", sa.String(40), nullable=False),
            sa.Column("description", sa.String(120), nullable=False),
            sa.Column("gondola_label", sa.String(80), nullable=True),
            sa.Column("source_updated_at", sa.DateTime(), nullable=True),
            sa.Column("synced_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("source_system", "source_chain_id", name="uq_retail_price_chain"),
        )

    if "retail_product_price_chains" not in tables:
        op.create_table(
            "retail_product_price_chains",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("product_id", sa.String(36), sa.ForeignKey("retail_products.id", ondelete="CASCADE"), nullable=False),
            sa.Column(
                "price_chain_id",
                sa.String(36),
                sa.ForeignKey("retail_price_chains.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("synced_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("product_id", "price_chain_id", name="uq_retail_product_price_chain"),
        )
        op.create_index("ix_retail_product_price_chains_product_id", "retail_product_price_chains", ["product_id"])
        op.create_index("ix_retail_product_price_chains_price_chain_id", "retail_product_price_chains", ["price_chain_id"])

    if "retail_offer_campaigns" not in tables:
        op.create_table(
            "retail_offer_campaigns",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
            sa.Column("source_system", sa.String(40), nullable=False, server_default="CISS"),
            sa.Column("source_offer_id", sa.String(40), nullable=False),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("starts_at", sa.DateTime(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("source_updated_at", sa.DateTime(), nullable=True),
            sa.Column("synced_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("store_id", "source_system", "source_offer_id", name="uq_retail_offer_campaign"),
        )
        op.create_index("ix_retail_offer_campaigns_store_id", "retail_offer_campaigns", ["store_id"])

    if "retail_offer_items" not in tables:
        op.create_table(
            "retail_offer_items",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "campaign_id",
                sa.String(36),
                sa.ForeignKey("retail_offer_campaigns.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("product_id", sa.String(36), sa.ForeignKey("retail_products.id", ondelete="CASCADE"), nullable=False),
            sa.Column(
                "price_chain_id",
                sa.String(36),
                sa.ForeignKey("retail_price_chains.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("regular_price", sa.Numeric(18, 4), nullable=True),
            sa.Column("offer_price", sa.Numeric(18, 4), nullable=True),
            sa.Column("raw_offer_price", sa.Numeric(18, 4), nullable=True),
            sa.Column("calculation_type", sa.String(30), nullable=False, server_default="DIRECT"),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("synced_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("campaign_id", "product_id", name="uq_retail_offer_item"),
        )
        op.create_index("ix_retail_offer_items_campaign_id", "retail_offer_items", ["campaign_id"])
        op.create_index("ix_retail_offer_items_product_id", "retail_offer_items", ["product_id"])


def downgrade() -> None:
    for t in (
        "retail_offer_items",
        "retail_offer_campaigns",
        "retail_product_price_chains",
        "retail_price_chains",
    ):
        op.drop_table(t)

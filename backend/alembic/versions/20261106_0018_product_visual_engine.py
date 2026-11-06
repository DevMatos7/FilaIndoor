"""DRC-4 — ProductMediaLink + visual content templates seed helper

Revision ID: 20261106_0018
Revises: 20261106_0017
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20261106_0018"
down_revision: Union[str, None] = "20261106_0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "product_media_links" not in tables:
        op.create_table(
            "product_media_links",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("product_id", sa.String(36), sa.ForeignKey("retail_products.id", ondelete="CASCADE"), nullable=False),
            sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=True),
            sa.Column(
                "media_asset_id",
                sa.String(36),
                sa.ForeignKey("media_assets.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("purpose", sa.String(20), nullable=False, server_default="PRIMARY"),
            sa.Column("source", sa.String(20), nullable=False, server_default="MANUAL"),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_product_media_links_product_id", "product_media_links", ["product_id"])
        op.create_index("ix_product_media_links_store_id", "product_media_links", ["store_id"])
        op.create_index("ix_product_media_links_media_asset_id", "product_media_links", ["media_asset_id"])
        op.create_index(
            "ix_product_media_links_product_store_purpose",
            "product_media_links",
            ["product_id", "store_id", "purpose"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "product_media_links" in tables:
        op.drop_table("product_media_links")

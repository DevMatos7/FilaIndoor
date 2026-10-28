"""Sprint 7 — media assets

Revision ID: 20261027_0005
Revises: 20261027_0004
Create Date: 2026-10-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20261027_0005"
down_revision: Union[str, None] = "20261027_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "media_assets" not in set(inspector.get_table_names()):
        op.create_table(
            "media_assets",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(180), nullable=False),
            sa.Column("media_type", sa.String(20), nullable=False),
            sa.Column("mime_type", sa.String(120), nullable=True),
            sa.Column("original_filename", sa.String(255), nullable=True),
            sa.Column("storage_key", sa.String(500), nullable=True),
            sa.Column("public_url", sa.String(500), nullable=False),
            sa.Column("size_bytes", sa.Integer(), nullable=True),
            sa.Column("duration_seconds", sa.Integer(), nullable=True),
            sa.Column("width", sa.Integer(), nullable=True),
            sa.Column("height", sa.Integer(), nullable=True),
            sa.Column("checksum", sa.String(64), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_media_assets_store_id", "media_assets", ["store_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "media_assets" in set(inspector.get_table_names()):
        op.drop_index("ix_media_assets_store_id", table_name="media_assets")
        op.drop_table("media_assets")

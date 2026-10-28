"""Sprint 13 — Toledo discovery checklist

Revision ID: 20261028_0011
Revises: 20261028_0010
Create Date: 2026-10-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20261028_0011"
down_revision: Union[str, None] = "20261028_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "toledo_discoveries" not in tables:
        op.create_table(
            "toledo_discoveries",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("store_id", sa.String(36), nullable=True),
            sa.Column("environment_name", sa.String(120), nullable=False, server_default="default"),
            sa.Column("mgv_version", sa.String(80), nullable=True),
            sa.Column("mit_version", sa.String(80), nullable=True),
            sa.Column("mit_cloud", sa.Boolean(), nullable=True),
            sa.Column("mit_cloud_url", sa.String(500), nullable=True),
            sa.Column("license_notes", sa.Text(), nullable=True),
            sa.Column("stores_notes", sa.Text(), nullable=True),
            sa.Column("players_notes", sa.Text(), nullable=True),
            sa.Column("api_enabled", sa.Boolean(), nullable=True),
            sa.Column("api_base_url", sa.String(500), nullable=True),
            sa.Column("auth_type", sa.String(80), nullable=True),
            sa.Column("integration_key_configured", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("network_notes", sa.Text(), nullable=True),
            sa.Column("docs_compared", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("confirmed_capabilities", sa.JSON(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("mode_intent", sa.String(40), nullable=False, server_default="NATIVE"),
            sa.Column("updated_by", sa.String(120), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_toledo_discoveries_store_id", "toledo_discoveries", ["store_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if "toledo_discoveries" in set(inspect(bind).get_table_names()):
        op.drop_table("toledo_discoveries")

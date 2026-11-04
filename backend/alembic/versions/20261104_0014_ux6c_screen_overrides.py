"""UX-6C — Screen Override Engine

Revision ID: 20261104_0014
Revises: 20261103_0013
Create Date: 2026-11-04

- screen_overrides table
- UX-6B pre-flight: global slug uniqueness already present
  (uq_layout_templates_global_slug WHERE store_id IS NULL) — no change needed.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20261104_0014"
down_revision: Union[str, None] = "20261103_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())

    # Pre-flight UX-6B: ensure partial unique for global slugs exists (idempotent)
    if "layout_templates" in tables:
        indexes = {ix["name"] for ix in inspect(bind).get_indexes("layout_templates")}
        if "uq_layout_templates_global_slug" not in indexes:
            op.create_index(
                "uq_layout_templates_global_slug",
                "layout_templates",
                ["slug"],
                unique=True,
                postgresql_where=sa.text("store_id IS NULL"),
                sqlite_where=sa.text("store_id IS NULL"),
            )

    if "screen_overrides" not in tables:
        op.create_table(
            "screen_overrides",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
            sa.Column("override_type", sa.String(40), nullable=False),
            sa.Column("priority", sa.Integer(), nullable=False),
            sa.Column("target_scope", sa.String(40), nullable=False),
            sa.Column("target_id", sa.String(36), nullable=True),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("starts_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("cancelled_at", sa.DateTime(), nullable=True),
            sa.Column("dedupe_key", sa.String(180), nullable=True),
            sa.Column("source_type", sa.String(40), nullable=True),
            sa.Column("source_id", sa.String(80), nullable=True),
            sa.Column("created_by_user_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_screen_overrides_store_id", "screen_overrides", ["store_id"])
        op.create_index("ix_screen_overrides_override_type", "screen_overrides", ["override_type"])
        op.create_index("ix_screen_overrides_priority", "screen_overrides", ["priority"])
        op.create_index("ix_screen_overrides_target_scope", "screen_overrides", ["target_scope"])
        op.create_index("ix_screen_overrides_target_id", "screen_overrides", ["target_id"])
        op.create_index("ix_screen_overrides_starts_at", "screen_overrides", ["starts_at"])
        op.create_index("ix_screen_overrides_expires_at", "screen_overrides", ["expires_at"])
        op.create_index("ix_screen_overrides_dedupe_key", "screen_overrides", ["dedupe_key"])
        op.create_index(
            "ix_screen_overrides_active_lookup",
            "screen_overrides",
            ["store_id", "priority", "starts_at", "expires_at"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "screen_overrides" in tables:
        op.drop_table("screen_overrides")
    # Do not drop UX-6B partial unique on downgrade of UX-6C

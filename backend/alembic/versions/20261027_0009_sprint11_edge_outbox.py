"""Sprint 11 — edge outbox events

Revision ID: 20261027_0009
Revises: 20261027_0008
Create Date: 2026-10-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20261027_0009"
down_revision: Union[str, None] = "20261027_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "edge_outbox_events" not in tables:
        op.create_table(
            "edge_outbox_events",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("event_id", sa.String(64), nullable=False),
            sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
            sa.Column("origin_device", sa.String(120), nullable=True),
            sa.Column("origin_edge", sa.String(80), nullable=False, server_default="store-edge"),
            sa.Column("event_type", sa.String(60), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("occurred_at", sa.DateTime(), nullable=False),
            sa.Column("sync_status", sa.String(20), nullable=False, server_default="PENDING"),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("synced_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("event_id", name="uq_edge_outbox_event_id"),
        )
        op.create_index("ix_edge_outbox_events_store_id", "edge_outbox_events", ["store_id"])
        op.create_index("ix_edge_outbox_store_status", "edge_outbox_events", ["store_id", "sync_status"])
        op.create_index("ix_edge_outbox_occurred", "edge_outbox_events", ["occurred_at"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "edge_outbox_events" in set(inspector.get_table_names()):
        op.drop_table("edge_outbox_events")

"""Sprint 2 — kiosk + print_jobs

Revision ID: 20261027_0002
Revises: 20261027_0001
Create Date: 2026-10-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20261027_0002"
down_revision: Union[str, None] = "20261027_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    queue_cols = {c["name"] for c in inspector.get_columns("queues")}

    if "kiosk_enabled" not in queue_cols:
        op.add_column("queues", sa.Column("kiosk_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    if "kiosk_token" not in queue_cols:
        op.add_column("queues", sa.Column("kiosk_token", sa.String(length=120), nullable=True))
    if "department_display_name" not in queue_cols:
        op.add_column("queues", sa.Column("department_display_name", sa.String(length=180), nullable=True))

    indexes = {ix["name"] for ix in inspector.get_indexes("queues")}
    if "ix_queues_kiosk_token" not in indexes:
        op.create_index("ix_queues_kiosk_token", "queues", ["kiosk_token"])

    tables = set(inspector.get_table_names())
    if "print_jobs" not in tables:
        op.create_table(
            "print_jobs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("queue_id", sa.String(36), sa.ForeignKey("queues.id", ondelete="CASCADE"), nullable=False),
            sa.Column("ticket_id", sa.String(36), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
            sa.Column("provider", sa.String(40), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("payload_preview", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_print_jobs_ticket", "print_jobs", ["ticket_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "print_jobs" in tables:
        op.drop_index("ix_print_jobs_ticket", table_name="print_jobs")
        op.drop_table("print_jobs")

    indexes = {ix["name"] for ix in inspector.get_indexes("queues")}
    if "ix_queues_kiosk_token" in indexes:
        op.drop_index("ix_queues_kiosk_token", table_name="queues")

    queue_cols = {c["name"] for c in inspector.get_columns("queues")}
    if "department_display_name" in queue_cols:
        op.drop_column("queues", "department_display_name")
    if "kiosk_token" in queue_cols:
        op.drop_column("queues", "kiosk_token")
    if "kiosk_enabled" in queue_cols:
        op.drop_column("queues", "kiosk_enabled")

"""Sprint 15 — REAL+ virtual tickets + notifications

Revision ID: 20261028_0012
Revises: 20261028_0011
Create Date: 2026-10-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20261028_0012"
down_revision: Union[str, None] = "20261028_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())

    if "virtual_tickets" not in tables:
        op.create_table(
            "virtual_tickets",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("ticket_id", sa.String(36), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
            sa.Column("queue_id", sa.String(36), sa.ForeignKey("queues.id", ondelete="CASCADE"), nullable=False),
            sa.Column("tracking_token", sa.String(64), nullable=False),
            sa.Column("customer_label", sa.String(120), nullable=True),
            sa.Column("presence_status", sa.String(30), nullable=False, server_default="WAITING_REMOTE"),
            sa.Column("notify_when_ahead", sa.Integer(), nullable=False, server_default="2"),
            sa.Column("push_endpoint", sa.Text(), nullable=True),
            sa.Column("checked_in_at", sa.DateTime(), nullable=True),
            sa.Column("last_position", sa.Integer(), nullable=True),
            sa.Column("last_notified_ahead", sa.Integer(), nullable=True),
            sa.Column("metadata", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("tracking_token", name="uq_virtual_tickets_tracking"),
        )
        op.create_index("ix_virtual_tickets_ticket_id", "virtual_tickets", ["ticket_id"])
        op.create_index("ix_virtual_tickets_queue_id", "virtual_tickets", ["queue_id"])

    if "virtual_notifications" not in tables:
        op.create_table(
            "virtual_notifications",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "virtual_ticket_id",
                sa.String(36),
                sa.ForeignKey("virtual_tickets.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("channel", sa.String(40), nullable=False, server_default="IN_APP"),
            sa.Column("title", sa.String(180), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("delivered", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_virtual_notifications_virtual_ticket_id", "virtual_notifications", ["virtual_ticket_id"])
        op.create_index(
            "ix_virtual_notifications_virtual",
            "virtual_notifications",
            ["virtual_ticket_id", "created_at"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "virtual_notifications" in tables:
        op.drop_table("virtual_notifications")
    if "virtual_tickets" in tables:
        op.drop_table("virtual_tickets")

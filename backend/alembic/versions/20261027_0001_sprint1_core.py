"""Sprint 1 — core org + fila

Revision ID: 20261027_0001
Revises:
Create Date: 2026-10-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261027_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("external_code", sa.String(80), nullable=True),
        sa.Column("name", sa.String(180), nullable=False, unique=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_companies_external_code", "companies", ["external_code"])

    op.create_table(
        "stores",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_code", sa.String(80), nullable=True),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="America/Sao_Paulo"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_stores_company_id", "stores", ["company_id"])
    op.create_index("ix_stores_external_code", "stores", ["external_code"])

    op.create_table(
        "departments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_departments_store_id", "departments", ["store_id"])

    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(180), nullable=False),
        sa.Column("hashed_password", sa.Text(), nullable=False),
        sa.Column("role", sa.String(40), nullable=False, server_default="operator"),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id", ondelete="SET NULL"), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "queues",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("department_id", sa.String(36), sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="OPEN"),
        sa.Column("normal_prefix", sa.String(8), nullable=False, server_default="A"),
        sa.Column("priority_prefix", sa.String(8), nullable=False, server_default="P"),
        sa.Column("digits", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("initial_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("final_number", sa.Integer(), nullable=False, server_default="999"),
        sa.Column("reset_policy", sa.String(20), nullable=False, server_default="DAILY"),
        sa.Column("priority_strategy", sa.String(20), nullable=False, server_default="WEIGHTED"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_queues_department_id", "queues", ["department_id"])

    op.create_table(
        "queue_priority_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("queue_id", sa.String(36), sa.ForeignKey("queues.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("normal_weight", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("priority_weight", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("priority_max_wait_seconds", sa.Integer(), nullable=False, server_default="600"),
        sa.Column("normal_max_wait_seconds", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "queue_sequences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("queue_id", sa.String(36), sa.ForeignKey("queues.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ticket_type", sa.String(20), nullable=False),
        sa.Column("period_key", sa.String(32), nullable=False, server_default="default"),
        sa.Column("current_number", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("queue_id", "ticket_type", "period_key", name="uq_queue_seq"),
    )

    op.create_table(
        "tickets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("queue_id", sa.String(36), sa.ForeignKey("queues.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("display_number", sa.String(32), nullable=False),
        sa.Column("period_key", sa.String(32), nullable=False, server_default="default"),
        sa.Column("ticket_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="WAITING"),
        sa.Column("issued_at", sa.DateTime(), nullable=False),
        sa.Column("called_at", sa.DateTime(), nullable=True),
        sa.Column("service_started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("no_show_at", sa.DateTime(), nullable=True),
        sa.Column("terminal_id", sa.String(36), nullable=True),
        sa.Column("operator_id", sa.String(36), nullable=True),
        sa.Column("source", sa.String(20), nullable=False, server_default="KIOSK"),
        sa.Column("source_reference", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("queue_id", "display_number", "period_key", name="uq_ticket_display"),
    )
    op.create_index("ix_tickets_queue_status_issued", "tickets", ["queue_id", "status", "issued_at"])
    op.create_index(
        "ix_tickets_queue_type_status_issued",
        "tickets",
        ["queue_id", "ticket_type", "status", "issued_at"],
    )

    op.create_table(
        "ticket_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ticket_id", sa.String(36), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("event_at", sa.DateTime(), nullable=False),
        sa.Column("operator_id", sa.String(36), nullable=True),
        sa.Column("terminal_id", sa.String(36), nullable=True),
        sa.Column("device_id", sa.String(36), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
    )
    op.create_index("ix_ticket_events_ticket_at", "ticket_events", ["ticket_id", "event_at"])

    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("scope", sa.String(120), nullable=False),
        sa.Column("key", sa.String(120), nullable=False),
        sa.Column("response_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("scope", "key", name="uq_idempotency_scope_key"),
    )


def downgrade() -> None:
    op.drop_table("idempotency_records")
    op.drop_table("ticket_events")
    op.drop_table("tickets")
    op.drop_table("queue_sequences")
    op.drop_table("queue_priority_rules")
    op.drop_table("queues")
    op.drop_table("users")
    op.drop_table("departments")
    op.drop_table("stores")
    op.drop_table("companies")

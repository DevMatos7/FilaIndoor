"""Sprint 3 — terminals

Revision ID: 20261027_0003
Revises: 20261027_0002
Create Date: 2026-10-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20261027_0003"
down_revision: Union[str, None] = "20261027_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "terminals" not in tables:
        op.create_table(
            "terminals",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("department_id", sa.String(36), sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("code", sa.String(40), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("department_id", "code", name="uq_terminal_dept_code"),
        )
        op.create_index("ix_terminals_department_id", "terminals", ["department_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "terminals" in set(inspector.get_table_names()):
        op.drop_index("ix_terminals_department_id", table_name="terminals")
        op.drop_table("terminals")

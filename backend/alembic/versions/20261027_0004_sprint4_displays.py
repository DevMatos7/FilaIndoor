"""Sprint 4 — displays

Revision ID: 20261027_0004
Revises: 20261027_0003
Create Date: 2026-10-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20261027_0004"
down_revision: Union[str, None] = "20261027_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "displays" not in set(inspector.get_table_names()):
        op.create_table(
            "displays",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
            sa.Column("department_id", sa.String(36), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
            sa.Column("queue_id", sa.String(36), sa.ForeignKey("queues.id", ondelete="SET NULL"), nullable=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("code", sa.String(40), nullable=False),
            sa.Column("token", sa.String(120), nullable=False),
            sa.Column("audio_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column(
                "audio_template",
                sa.String(255),
                nullable=False,
                server_default="Senha {number}. Favor dirigir-se ao {department}.",
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("store_id", "code", name="uq_display_store_code"),
            sa.UniqueConstraint("token", name="uq_displays_token"),
        )
        op.create_index("ix_displays_store_id", "displays", ["store_id"])
        op.create_index("ix_displays_token", "displays", ["token"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "displays" in set(inspector.get_table_names()):
        op.drop_index("ix_displays_token", table_name="displays")
        op.drop_index("ix_displays_store_id", table_name="displays")
        op.drop_table("displays")

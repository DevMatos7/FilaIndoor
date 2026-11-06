"""DRC-5 — RetailSyncRun.trigger + watermark consecutive_failures

Revision ID: 20261106_0019
Revises: 20261106_0018
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20261106_0019"
down_revision: Union[str, None] = "20261106_0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())

    if "retail_sync_runs" in tables:
        cols = {c["name"] for c in insp.get_columns("retail_sync_runs")}
        if "trigger" not in cols:
            op.add_column(
                "retail_sync_runs",
                sa.Column("trigger", sa.String(20), nullable=False, server_default="MANUAL"),
            )

    if "retail_sync_watermarks" in tables:
        cols = {c["name"] for c in insp.get_columns("retail_sync_watermarks")}
        if "consecutive_failures" not in cols:
            op.add_column(
                "retail_sync_watermarks",
                sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())
    if "retail_sync_runs" in tables:
        cols = {c["name"] for c in insp.get_columns("retail_sync_runs")}
        if "trigger" in cols:
            op.drop_column("retail_sync_runs", "trigger")
    if "retail_sync_watermarks" in tables:
        cols = {c["name"] for c in insp.get_columns("retail_sync_watermarks")}
        if "consecutive_failures" in cols:
            op.drop_column("retail_sync_watermarks", "consecutive_failures")

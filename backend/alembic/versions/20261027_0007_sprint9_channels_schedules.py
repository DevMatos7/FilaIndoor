"""Sprint 9 — channels, screen groups, schedules

Revision ID: 20261027_0007
Revises: 20261027_0006
Create Date: 2026-10-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20261027_0007"
down_revision: Union[str, None] = "20261027_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "channels" not in tables:
        op.create_table(
            "channels",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(180), nullable=False),
            sa.Column("layout", sa.String(60), nullable=False, server_default="queue_media_split"),
            sa.Column("default_playlist_id", sa.String(36), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_channels_store_id", "channels", ["store_id"])

    if "screen_groups" not in tables:
        op.create_table(
            "screen_groups",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
            sa.Column("channel_id", sa.String(36), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(180), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_screen_groups_store_id", "screen_groups", ["store_id"])
        op.create_index("ix_screen_groups_channel_id", "screen_groups", ["channel_id"])

    if "schedules" not in tables:
        op.create_table(
            "schedules",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("channel_id", sa.String(36), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
            sa.Column("playlist_id", sa.String(36), sa.ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(180), nullable=False, server_default="Agenda"),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("start_time", sa.Time(), nullable=False),
            sa.Column("end_time", sa.Time(), nullable=False),
            sa.Column("days_of_week", sa.String(32), nullable=False, server_default="0,1,2,3,4,5,6"),
            sa.Column("priority", sa.String(20), nullable=False, server_default="NORMAL"),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_schedules_channel_id", "schedules", ["channel_id"])
        op.create_index("ix_schedules_playlist_id", "schedules", ["playlist_id"])

    if "displays" in tables:
        cols = {c["name"] for c in inspector.get_columns("displays")}
        if "channel_id" not in cols:
            op.add_column("displays", sa.Column("channel_id", sa.String(36), nullable=True))
            op.create_index("ix_displays_channel_id", "displays", ["channel_id"])
        if "screen_group_id" not in cols:
            op.add_column("displays", sa.Column("screen_group_id", sa.String(36), nullable=True))
            op.create_index("ix_displays_screen_group_id", "displays", ["screen_group_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "displays" in tables:
        cols = {c["name"] for c in inspector.get_columns("displays")}
        if "screen_group_id" in cols:
            op.drop_index("ix_displays_screen_group_id", table_name="displays")
            op.drop_column("displays", "screen_group_id")
        if "channel_id" in cols:
            op.drop_index("ix_displays_channel_id", table_name="displays")
            op.drop_column("displays", "channel_id")
    if "schedules" in tables:
        op.drop_table("schedules")
    if "screen_groups" in tables:
        op.drop_table("screen_groups")
    if "channels" in tables:
        op.drop_table("channels")

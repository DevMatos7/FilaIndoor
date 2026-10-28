"""Sprint 8 — playlists

Revision ID: 20261027_0006
Revises: 20261027_0005
Create Date: 2026-10-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20261027_0006"
down_revision: Union[str, None] = "20261027_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "playlists" not in tables:
        op.create_table(
            "playlists",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(180), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_playlists_store_id", "playlists", ["store_id"])

    if "playlist_items" not in tables:
        op.create_table(
            "playlist_items",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("playlist_id", sa.String(36), sa.ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False),
            sa.Column("asset_id", sa.String(36), sa.ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="10"),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_playlist_items_playlist_id", "playlist_items", ["playlist_id"])
        op.create_index("ix_playlist_items_asset_id", "playlist_items", ["asset_id"])

    cols = {c["name"] for c in inspector.get_columns("displays")} if "displays" in tables else set()
    if "playlist_id" not in cols:
        op.add_column("displays", sa.Column("playlist_id", sa.String(36), nullable=True))
        op.create_index("ix_displays_playlist_id", "displays", ["playlist_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "displays" in tables:
        cols = {c["name"] for c in inspector.get_columns("displays")}
        if "playlist_id" in cols:
            op.drop_index("ix_displays_playlist_id", table_name="displays")
            op.drop_column("displays", "playlist_id")
    if "playlist_items" in tables:
        op.drop_table("playlist_items")
    if "playlists" in tables:
        op.drop_table("playlists")

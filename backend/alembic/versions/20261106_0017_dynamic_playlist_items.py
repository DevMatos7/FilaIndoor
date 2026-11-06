"""DRC-3 — PlaylistItem MEDIA|DYNAMIC

Revision ID: 20261106_0017
Revises: 20261105_0016
Create Date: 2026-11-06

Downgrade: fails if any DYNAMIC items exist (safe).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision: str = "20261106_0017"
down_revision: Union[str, None] = "20261105_0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in inspect(bind).get_columns("playlist_items")}

    if "item_type" not in cols:
        op.add_column(
            "playlist_items",
            sa.Column("item_type", sa.String(20), nullable=False, server_default="MEDIA"),
        )
    if "dynamic_content_id" not in cols:
        op.add_column(
            "playlist_items",
            sa.Column(
                "dynamic_content_id",
                sa.String(36),
                sa.ForeignKey("dynamic_contents.id", ondelete="RESTRICT"),
                nullable=True,
            ),
        )
        op.create_index("ix_playlist_items_dynamic_content_id", "playlist_items", ["dynamic_content_id"])
    if "duration_source" not in cols:
        op.add_column(
            "playlist_items",
            sa.Column("duration_source", sa.String(20), nullable=False, server_default="SOURCE"),
        )
    if "config" not in cols:
        op.add_column("playlist_items", sa.Column("config", sa.JSON(), nullable=True))

    # Make asset_id nullable (preserve existing FKs)
    op.alter_column("playlist_items", "asset_id", existing_type=sa.String(36), nullable=True)

    # Backfill
    op.execute(text("UPDATE playlist_items SET item_type = 'MEDIA' WHERE item_type IS NULL OR item_type = ''"))

    # Check constraint
    dialect = bind.dialect.name
    if dialect == "postgresql":
        op.execute(
            text(
                """
                ALTER TABLE playlist_items DROP CONSTRAINT IF EXISTS ck_playlist_items_media_or_dynamic;
                ALTER TABLE playlist_items ADD CONSTRAINT ck_playlist_items_media_or_dynamic CHECK (
                  (item_type = 'MEDIA' AND asset_id IS NOT NULL AND dynamic_content_id IS NULL)
                  OR
                  (item_type = 'DYNAMIC' AND asset_id IS NULL AND dynamic_content_id IS NOT NULL)
                );
                """
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    count = bind.execute(
        text("SELECT COUNT(*) FROM playlist_items WHERE item_type = 'DYNAMIC' AND active = true")
    ).scalar()
    if count and int(count) > 0:
        raise RuntimeError(
            f"Downgrade bloqueado: existem {count} PlaylistItem(s) DYNAMIC ativos. "
            "Remova-os da playlist antes do downgrade."
        )
    if bind.dialect.name == "postgresql":
        op.execute(text("ALTER TABLE playlist_items DROP CONSTRAINT IF EXISTS ck_playlist_items_media_or_dynamic"))
    # Drop added columns (leave asset_id nullable — safer than forcing NOT NULL)
    cols = {c["name"] for c in inspect(bind).get_columns("playlist_items")}
    for col in ("config", "duration_source", "dynamic_content_id", "item_type"):
        if col in cols:
            op.drop_column("playlist_items", col)

"""Sprint 10 — devices + device_heartbeats

Revision ID: 20261027_0008
Revises: 20261027_0007
Create Date: 2026-10-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20261027_0008"
down_revision: Union[str, None] = "20261027_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "devices" not in tables:
        op.create_table(
            "devices",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id", ondelete="SET NULL"), nullable=True),
            sa.Column(
                "department_id", sa.String(36), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
            ),
            sa.Column("display_id", sa.String(36), sa.ForeignKey("displays.id", ondelete="SET NULL"), nullable=True),
            sa.Column("device_type", sa.String(20), nullable=False, server_default="DISPLAY"),
            sa.Column("name", sa.String(180), nullable=False),
            sa.Column("device_uuid", sa.String(64), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="OFFLINE"),
            sa.Column("audio_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("last_seen_at", sa.DateTime(), nullable=True),
            sa.Column("app_version", sa.String(40), nullable=True),
            sa.Column("config_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("ip_address", sa.String(64), nullable=True),
            sa.Column("pairing_code", sa.String(12), nullable=True),
            sa.Column("pairing_expires_at", sa.DateTime(), nullable=True),
            sa.Column("enrolled_at", sa.DateTime(), nullable=True),
            sa.Column("metadata", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("device_uuid", name="uq_devices_device_uuid"),
            sa.UniqueConstraint("display_id", name="uq_devices_display_id"),
        )
        op.create_index("ix_devices_store_id", "devices", ["store_id"])
        op.create_index("ix_devices_department_id", "devices", ["department_id"])
        op.create_index("ix_devices_display_id", "devices", ["display_id"])
        op.create_index("ix_devices_device_uuid", "devices", ["device_uuid"])
        op.create_index("ix_devices_store_status", "devices", ["store_id", "status"])
        op.create_index("ix_devices_pairing_code", "devices", ["pairing_code"])

    if "device_heartbeats" not in tables:
        op.create_table(
            "device_heartbeats",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("device_id", sa.String(36), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
            sa.Column("timestamp", sa.DateTime(), nullable=False),
            sa.Column("ip", sa.String(64), nullable=True),
            sa.Column("app_version", sa.String(40), nullable=True),
            sa.Column("free_storage_mb", sa.Integer(), nullable=True),
            sa.Column("playlist_version", sa.Integer(), nullable=True),
            sa.Column("metadata", sa.JSON(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
        )
        op.create_index("ix_device_heartbeats_device_id", "device_heartbeats", ["device_id"])
        op.create_index("ix_device_heartbeats_device_ts", "device_heartbeats", ["device_id", "timestamp"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "device_heartbeats" in tables:
        op.drop_table("device_heartbeats")
    if "devices" in tables:
        op.drop_table("devices")

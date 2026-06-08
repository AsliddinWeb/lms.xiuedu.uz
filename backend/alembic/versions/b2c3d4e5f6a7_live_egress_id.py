"""live egress_id — server-side recording (Phase 32)

LiveRecording.egress_id — egress webhook'ni yozuvga bog'lash uchun.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "live_recordings",
        sa.Column("egress_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_live_recordings_egress_id", "live_recordings", ["egress_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_live_recordings_egress_id", table_name="live_recordings")
    op.drop_column("live_recordings", "egress_id")

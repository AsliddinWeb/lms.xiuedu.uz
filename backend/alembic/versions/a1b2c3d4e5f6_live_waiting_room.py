"""live waiting room — admission (Phase 31)

LiveSession.requires_approval + live_admissions jadvali (waiting room).

Revision ID: a1b2c3d4e5f6
Revises: f2a3b4c5d6e7
Create Date: 2026-06-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "live_sessions",
        sa.Column(
            "requires_approval",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_table(
        "live_admissions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["live_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "user_id", name="uq_live_admission_session_user"),
    )
    op.create_index("ix_live_admissions_session_id", "live_admissions", ["session_id"])
    op.create_index("ix_live_admissions_user_id", "live_admissions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_live_admissions_user_id", table_name="live_admissions")
    op.drop_index("ix_live_admissions_session_id", table_name="live_admissions")
    op.drop_table("live_admissions")
    op.drop_column("live_sessions", "requires_approval")

"""drop peer reviews (feature removed)

Peer review xususiyati to'liq olib tashlandi: `peer_reviews` jadvali va
`assignments` jadvalidagi peer_review_enabled / peer_reviews_per_submission
ustunlari o'chiriladi.

Revision ID: e1f2a3b4c5d6
Revises: c3a07e9adcc9
Create Date: 2026-06-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e1f2a3b4c5d6"
down_revision = "c3a07e9adcc9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("peer_reviews")
    op.drop_column("assignments", "peer_reviews_per_submission")
    op.drop_column("assignments", "peer_review_enabled")


def downgrade() -> None:
    op.add_column(
        "assignments",
        sa.Column(
            "peer_review_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "assignments",
        sa.Column(
            "peer_reviews_per_submission",
            sa.Integer(),
            nullable=False,
            server_default="3",
        ),
    )
    op.create_table(
        "peer_reviews",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("submission_id", sa.BigInteger(), nullable=False),
        sa.Column("reviewer_id", sa.BigInteger(), nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("rubric_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("submission_id", "reviewer_id", name="uq_peer_review_sub_reviewer"),
    )
    op.create_index("ix_peer_reviews_submission_id", "peer_reviews", ["submission_id"])
    op.create_index("ix_peer_reviews_reviewer_id", "peer_reviews", ["reviewer_id"])

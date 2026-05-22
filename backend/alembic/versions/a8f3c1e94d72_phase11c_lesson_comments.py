"""phase11c_lesson_comments

Revision ID: a8f3c1e94d72
Revises: c2e850ab0653
Create Date: 2026-05-21 16:00:00.000000

Phase 11c — Dars izohlari (lesson comments).

Forum thread'lardan farqli — comments lesson darajasida, yengil va
faqat 1 darajali reply (parent_comment_id self-FK). Talaba va o'qituvchi
har ikkalasi yozishi mumkin. Like toggle.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "a8f3c1e94d72"
down_revision: str | None = "c2e850ab0653"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lesson_comments",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "lesson_id",
            sa.BigInteger(),
            sa.ForeignKey("lessons.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "author_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        # 1-darajali reply (null = top-level)
        sa.Column(
            "parent_comment_id",
            sa.BigInteger(),
            sa.ForeignKey("lesson_comments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("like_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_lesson_comments_lesson_created",
        "lesson_comments",
        ["lesson_id", sa.text("created_at DESC")],
    )

    op.create_table(
        "lesson_comment_likes",
        sa.Column(
            "comment_id",
            sa.BigInteger(),
            sa.ForeignKey("lesson_comments.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("lesson_comment_likes")
    op.drop_index("ix_lesson_comments_lesson_created", table_name="lesson_comments")
    op.drop_table("lesson_comments")

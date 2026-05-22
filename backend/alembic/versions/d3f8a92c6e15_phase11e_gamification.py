"""phase11e_gamification

Revision ID: d3f8a92c6e15
Revises: b6d2e54f3a91
Create Date: 2026-05-21 18:00:00.000000

Phase 11e — Gamification: badge, ball va leaderboard.

Jadvallar:
    badges                — nishonlar katalogi (code unique, kategoriya, ikon)
    user_badges           — user'ga berilgan nishonlar (junction)
    user_points           — har bir user'ning jami balli (cache)
    gamification_events   — xom event log (audit + qayta hisoblash uchun)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "d3f8a92c6e15"
down_revision: str | None = "b6d2e54f3a91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ========================================================================
    # badges — katalog
    # ========================================================================
    op.create_table(
        "badges",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        # Kod — kod orqali award qilinadi: 'first_course', 'streak_7', etc.
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        # 'achievement' | 'progress' | 'social' | 'mastery'
        sa.Column("category", sa.String(40), nullable=False, server_default="achievement"),
        # MinIO yoki tashqi CDN URL
        sa.Column("icon_url", sa.Text(), nullable=True),
        # Award qilinganda beriladigan ball (default 0)
        sa.Column("points_reward", sa.Integer(), nullable=False, server_default="0"),
        # Yashirin badge — talaba avval olmaguncha katalogda ko'rinmaydi
        sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )

    # ========================================================================
    # user_badges — junction
    # ========================================================================
    op.create_table(
        "user_badges",
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "badge_id",
            sa.BigInteger(),
            sa.ForeignKey("badges.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "awarded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        # Context: qaysi kurs, qaysi mavzu — JSON metadata
        sa.Column(
            "context",
            sa.dialects.postgresql.JSONB(),
            nullable=True,
        ),
    )

    # ========================================================================
    # user_points — jami ball cache (denormallashtirilgan)
    # ========================================================================
    op.create_table(
        "user_points",
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("total_points", sa.Integer(), nullable=False, server_default="0"),
        # Joriy hafta/oy uchun alohida tracker — leaderboard variantlari uchun
        sa.Column("weekly_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("monthly_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "weekly_reset_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "monthly_reset_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    # Leaderboard top-N uchun
    op.create_index(
        "ix_user_points_total_desc",
        "user_points",
        [sa.text("total_points DESC")],
    )

    # ========================================================================
    # gamification_events — xom log
    # ========================================================================
    op.create_table(
        "gamification_events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # 'course.completed' | 'lesson.completed' | 'exam.passed' | 'comment.created' | etc.
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("points_awarded", sa.Integer(), nullable=False, server_default="0"),
        # Idempotency: bir xil event uchun bir xil key — duplikatdan saqlanish
        sa.Column("dedupe_key", sa.String(200), nullable=True),
        sa.Column(
            "context",
            sa.dialects.postgresql.JSONB(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_gamif_events_user_created",
        "gamification_events",
        ["user_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_gamif_events_dedupe",
        "gamification_events",
        ["dedupe_key"],
        unique=True,
        postgresql_where=sa.text("dedupe_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_gamif_events_dedupe", table_name="gamification_events")
    op.drop_index("ix_gamif_events_user_created", table_name="gamification_events")
    op.drop_table("gamification_events")
    op.drop_index("ix_user_points_total_desc", table_name="user_points")
    op.drop_table("user_points")
    op.drop_table("user_badges")
    op.drop_table("badges")

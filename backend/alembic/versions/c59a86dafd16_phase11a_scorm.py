"""phase11a_scorm

Revision ID: c59a86dafd16
Revises: db76fb1c4f7b
Create Date: 2026-05-21 14:00:00.000000

Phase 11a — SCORM 1.2/2004 player.

Yangi jadvalllar:
    - scorm_packages   — yuklangan SCORM ZIP paket metadata (manifestdan)
    - scorm_attempts   — talaba sessiyalari + CMI ma'lumotlari

ContentItem.type yangi qiymat oladi: 'scorm'.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "c59a86dafd16"
down_revision: str | None = "db76fb1c4f7b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # SCORM paket — har content_item uchun 1 ta SCORM paket (1:1)
    op.create_table(
        "scorm_packages",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "content_item_id",
            sa.BigInteger(),
            sa.ForeignKey("content_items.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("version", sa.String(10), nullable=False),  # '1.2' | '2004'
        sa.Column("manifest_identifier", sa.String(255), nullable=True),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        # Iframe boshlovchi sahifa, e.g. 'shared/launchpage.html' (relative to package root)
        sa.Column("launch_url", sa.String(500), nullable=False),
        # MinIO bucket'dagi root prefix, e.g. 'scorm/{id}/'
        sa.Column("package_path", sa.String(500), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("mastery_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )

    # SCORM attempt — har user × paket × attempt_number
    op.create_table(
        "scorm_attempts",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "package_id",
            sa.BigInteger(),
            sa.ForeignKey("scorm_packages.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "lesson_id",
            sa.BigInteger(),
            sa.ForeignKey("lessons.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        # 'in_progress' | 'completed' | 'passed' | 'failed' | 'incomplete' | 'browsed'
        sa.Column(
            "status",
            sa.String(30),
            server_default="in_progress",
            nullable=False,
        ),
        # SCORM CMI data — JSONB (key-value, e.g. {'cmi.core.lesson_status': 'completed'})
        sa.Column(
            "cmi_data",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        # Cached numeric fields (derived from cmi_data for fast queries)
        sa.Column("score_raw", sa.Numeric(5, 2), nullable=True),
        sa.Column("score_min", sa.Numeric(5, 2), nullable=True),
        sa.Column("score_max", sa.Numeric(5, 2), nullable=True),
        # SCORM time format hh:mm:ss.ss — saqlashda string
        sa.Column("total_time", sa.String(20), nullable=True),
        sa.Column("session_time", sa.String(20), nullable=True),
        sa.Column("bookmark", sa.String(500), nullable=True),
        sa.Column("suspend_data", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_accessed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id",
            "package_id",
            "attempt_number",
            name="uq_scorm_attempt_user_package_number",
        ),
    )
    # Hot lookup: foydalanuvchining shu paket bo'yicha eng so'nggi sessiyasi
    op.create_index(
        "ix_scorm_attempts_user_package",
        "scorm_attempts",
        ["user_id", "package_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_scorm_attempts_user_package", table_name="scorm_attempts")
    op.drop_table("scorm_attempts")
    op.drop_table("scorm_packages")

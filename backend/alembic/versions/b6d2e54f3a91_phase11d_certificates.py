"""phase11d_certificates

Revision ID: b6d2e54f3a91
Revises: a8f3c1e94d72
Create Date: 2026-05-21 17:00:00.000000

Phase 11d — Kurs sertifikatlari + QR verifikatsiya.

`certificates` jadvali:
    id, user_id, course_id, certificate_number (unique), issued_at,
    revoked_at, pdf_path (MinIO), verification_code (unique short token),
    score_percentage (opsional, kurs umumiy bahosi).

Verifikatsiya: `verification_code` umumiy URL (public) orqali tekshiriladi —
QR kodda shu URL kodlangan.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "b6d2e54f3a91"
down_revision: str | None = "a8f3c1e94d72"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "certificates",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "course_id",
            sa.BigInteger(),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # Inson o'qiy oladigan raqam: XIU-2026-000123
        sa.Column(
            "certificate_number",
            sa.String(50),
            nullable=False,
            unique=True,
        ),
        # QR uchun qisqa token (URL safe, base32)
        sa.Column(
            "verification_code",
            sa.String(32),
            nullable=False,
            unique=True,
        ),
        sa.Column("score_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("pdf_path", sa.Text(), nullable=True),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoke_reason", sa.Text(), nullable=True),
    )
    # Bir kurs uchun bir user bitta sertifikat olishi
    op.create_index(
        "ix_certificates_user_course",
        "certificates",
        ["user_id", "course_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_certificates_user_course", table_name="certificates")
    op.drop_table("certificates")

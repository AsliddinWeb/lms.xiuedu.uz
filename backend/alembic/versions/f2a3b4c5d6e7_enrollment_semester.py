"""enrollment semester tags (Phase 25)

Enrollment'ga `academic_year` va `semester` ustunlari — baholar semestr tarixi uchun.

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-06-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f2a3b4c5d6e7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("enrollments", sa.Column("academic_year", sa.String(length=20), nullable=True))
    op.add_column("enrollments", sa.Column("semester", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("enrollments", "semester")
    op.drop_column("enrollments", "academic_year")

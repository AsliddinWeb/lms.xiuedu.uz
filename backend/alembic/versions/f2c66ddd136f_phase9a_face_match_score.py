"""phase9a_face_match_score

Revision ID: f2c66ddd136f
Revises: 9c975ce1c3e3
Create Date: 2026-05-18 11:16:04.135195

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f2c66ddd136f'
down_revision: str | None = '9c975ce1c3e3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('exam_proctoring_snapshots', sa.Column('face_match_score', sa.Numeric(precision=6, scale=4), nullable=True))


def downgrade() -> None:
    op.drop_column('exam_proctoring_snapshots', 'face_match_score')

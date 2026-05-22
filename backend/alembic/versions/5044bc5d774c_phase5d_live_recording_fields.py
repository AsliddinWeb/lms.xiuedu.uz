"""phase5d_live_recording_fields

Revision ID: 5044bc5d774c
Revises: d79a0f58f314
Create Date: 2026-05-11 10:14:06.102037

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '5044bc5d774c'
down_revision: str | None = 'd79a0f58f314'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('live_sessions', sa.Column('thumbnail_url', sa.Text(), nullable=True))
    op.add_column('live_sessions', sa.Column('recording_size_bytes', sa.BigInteger(), nullable=True))
    op.add_column('live_sessions', sa.Column('recording_duration_seconds', sa.Integer(), nullable=True))
    op.add_column('live_sessions', sa.Column('recording_mime_type', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('live_sessions', 'recording_mime_type')
    op.drop_column('live_sessions', 'recording_duration_seconds')
    op.drop_column('live_sessions', 'recording_size_bytes')
    op.drop_column('live_sessions', 'thumbnail_url')

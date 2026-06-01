"""course reviews

Revision ID: c3a07e9adcc9
Revises: d3f8a92c6e15
Create Date: 2026-06-01 11:51:52.445971

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c3a07e9adcc9'
down_revision: str | None = 'd3f8a92c6e15'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'course_reviews',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('course_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['course_id'],
            ['courses.id'],
            name=op.f('fk_course_reviews_course_id_courses'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            name=op.f('fk_course_reviews_user_id_users'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_course_reviews')),
        sa.UniqueConstraint(
            'course_id', 'user_id', name='uq_review_course_user'
        ),
    )
    op.create_index(
        'ix_course_reviews_course_id',
        'course_reviews',
        ['course_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_course_reviews_course_id', table_name='course_reviews')
    op.drop_table('course_reviews')

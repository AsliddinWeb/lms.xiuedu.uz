"""phase10b_index_cleanup

Revision ID: db76fb1c4f7b
Revises: 3389e08e185c
Create Date: 2026-05-21 11:50:00.000000

3389e08e185c (Phase 10b) da bir nechta tabni unique+index alohida yaratildi.
SQLAlchemy `index=True, unique=True` esa yagona unique index yaratadi.
Drift'ni bartaraf etish uchun duplicate'larni o'chiramiz.
"""
from collections.abc import Sequence

from alembic import op


revision: str = 'db76fb1c4f7b'
down_revision: str | None = '3389e08e185c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # users.hemis_login — drop separate unique constraint, recreate index as unique
    op.drop_constraint('uq_users_hemis_login', 'users', type_='unique')
    op.drop_index('ix_users_hemis_login', table_name='users')
    op.create_index('ix_users_hemis_login', 'users', ['hemis_login'], unique=True)

    # faculties.hemis_id — drop separate unique constraint, recreate index as unique
    op.drop_constraint('uq_faculties_hemis_id', 'faculties', type_='unique')
    op.drop_index('ix_faculties_hemis_id', table_name='faculties')
    op.create_index('ix_faculties_hemis_id', 'faculties', ['hemis_id'], unique=True)

    # academic_groups: rename indexes to SQLAlchemy canonical naming
    op.drop_index('ix_academic_groups_faculty', table_name='academic_groups')
    op.drop_index('ix_academic_groups_specialty', table_name='academic_groups')
    op.create_index('ix_academic_groups_faculty_id', 'academic_groups', ['faculty_id'])
    op.create_index('ix_academic_groups_specialty_id', 'academic_groups', ['specialty_id'])


def downgrade() -> None:
    op.drop_index('ix_academic_groups_specialty_id', table_name='academic_groups')
    op.drop_index('ix_academic_groups_faculty_id', table_name='academic_groups')
    op.create_index('ix_academic_groups_specialty', 'academic_groups', ['specialty_id'])
    op.create_index('ix_academic_groups_faculty', 'academic_groups', ['faculty_id'])

    op.drop_index('ix_faculties_hemis_id', table_name='faculties')
    op.create_index('ix_faculties_hemis_id', 'faculties', ['hemis_id'])
    op.create_unique_constraint('uq_faculties_hemis_id', 'faculties', ['hemis_id'])

    op.drop_index('ix_users_hemis_login', table_name='users')
    op.create_index('ix_users_hemis_login', 'users', ['hemis_login'])
    op.create_unique_constraint('uq_users_hemis_login', 'users', ['hemis_login'])

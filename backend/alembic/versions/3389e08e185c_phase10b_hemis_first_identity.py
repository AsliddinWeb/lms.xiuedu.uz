"""phase10b_hemis_first_identity

Revision ID: 3389e08e185c
Revises: 94e69c4d01f8
Create Date: 2026-05-21 11:30:00.000000

Phase 10b — HEMIS-first identity refactor.

O'zgarishlar:
- users.email: NOT NULL + UNIQUE → NULLABLE + partial unique index
- users: hemis_login, hemis_data_hash, hemis_last_synced_at, group_id, current_semester_id,
  education_form, payment_form, student_status, staff_position, employment_form, employment_staff
- profiles: first_name, last_name, middle_name, country, region, district, social_category,
  poverty_level, accommodation, academic_degree, academic_title
- faculties: hemis_id, hemis_code, hemis_parent_id, structure_type, locality_type
- specialties: hemis_code
- curricula: hemis_id
- Yangi: academic_groups, academic_semesters, hemis_classifiers
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '3389e08e185c'
down_revision: str | None = '94e69c4d01f8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ============================================================
    # 1. academic_groups (yangi)
    # ============================================================
    op.create_table(
        'academic_groups',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('hemis_id', sa.Integer(), unique=True, nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('education_lang', sa.String(20), nullable=True),
        sa.Column('faculty_id', sa.BigInteger(),
                  sa.ForeignKey('faculties.id', ondelete='SET NULL'), nullable=True),
        sa.Column('specialty_id', sa.BigInteger(),
                  sa.ForeignKey('specialties.id', ondelete='SET NULL'), nullable=True),
        sa.Column('semester_hemis_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('hemis_last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('ix_academic_groups_faculty', 'academic_groups', ['faculty_id'])
    op.create_index('ix_academic_groups_specialty', 'academic_groups', ['specialty_id'])

    # ============================================================
    # 2. academic_semesters (yangi)
    # ============================================================
    op.create_table(
        'academic_semesters',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('hemis_id', sa.Integer(), unique=True, nullable=False),
        sa.Column('code', sa.String(20), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('education_year_code', sa.String(20), nullable=True),
        sa.Column('education_year_name', sa.String(50), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('hemis_last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
    )

    # ============================================================
    # 3. hemis_classifiers (yangi) — yagona registr
    # ============================================================
    op.create_table(
        'hemis_classifiers',
        sa.Column('type', sa.String(50), primary_key=True),
        sa.Column('code', sa.String(50), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('hemis_last_synced_at', sa.DateTime(timezone=True), nullable=True),
    )

    # ============================================================
    # 4. faculties — HEMIS field'lar
    # ============================================================
    op.add_column('faculties', sa.Column('hemis_id', sa.Integer(), nullable=True))
    op.add_column('faculties', sa.Column('hemis_code', sa.String(50), nullable=True))
    op.add_column('faculties', sa.Column('hemis_parent_id', sa.Integer(), nullable=True))
    op.add_column('faculties', sa.Column('structure_type', sa.String(50), nullable=True))
    op.add_column('faculties', sa.Column('locality_type', sa.String(50), nullable=True))
    op.create_unique_constraint('uq_faculties_hemis_id', 'faculties', ['hemis_id'])
    op.create_index('ix_faculties_hemis_id', 'faculties', ['hemis_id'])

    # ============================================================
    # 5. specialties — hemis_code
    # ============================================================
    op.add_column('specialties', sa.Column('hemis_code', sa.String(50), nullable=True))
    op.create_index('ix_specialties_hemis_code', 'specialties', ['hemis_code'])

    # ============================================================
    # 6. curricula — hemis_id
    # ============================================================
    op.add_column('curricula', sa.Column('hemis_id', sa.Integer(), nullable=True))
    op.create_unique_constraint('uq_curricula_hemis_id', 'curricula', ['hemis_id'])

    # ============================================================
    # 7. profiles — HEMIS ma'lumotlari
    # ============================================================
    op.add_column('profiles', sa.Column('first_name', sa.String(100), nullable=True))
    op.add_column('profiles', sa.Column('last_name', sa.String(100), nullable=True))
    op.add_column('profiles', sa.Column('middle_name', sa.String(100), nullable=True))
    op.add_column('profiles', sa.Column('country', sa.String(50), nullable=True))
    op.add_column('profiles', sa.Column('region', sa.String(100), nullable=True))
    op.add_column('profiles', sa.Column('district', sa.String(100), nullable=True))
    op.add_column('profiles', sa.Column('social_category', sa.String(50), nullable=True))
    op.add_column('profiles', sa.Column('poverty_level', sa.String(50), nullable=True))
    op.add_column('profiles', sa.Column('accommodation', sa.String(50), nullable=True))
    # Faqat employee uchun:
    op.add_column('profiles', sa.Column('academic_degree', sa.String(50), nullable=True))
    op.add_column('profiles', sa.Column('academic_title', sa.String(50), nullable=True))

    # ============================================================
    # 8. users — HEMIS-first identity fields
    # ============================================================
    # email NOT NULL + UNIQUE → NULLABLE + partial unique
    op.alter_column('users', 'email', nullable=True)
    # Drop existing unique constraint (might be index, depends on previous migration)
    # SQLAlchemy creates `ix_users_email` (non-unique index) AND a unique constraint named `users_email_key`
    op.drop_index('ix_users_email', table_name='users')
    # PostgreSQL'da implicit unique constraint default ravishda `users_email_key` deb nomlanadi
    op.execute('ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key')
    # Partial unique index — faqat NOT NULL qatorlar uchun
    op.create_index(
        'ux_users_email_notnull', 'users', ['email'],
        unique=True, postgresql_where=sa.text('email IS NOT NULL'),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # HEMIS identity fields
    op.add_column('users', sa.Column('hemis_login', sa.String(50), nullable=True))
    op.create_unique_constraint('uq_users_hemis_login', 'users', ['hemis_login'])
    op.create_index('ix_users_hemis_login', 'users', ['hemis_login'])

    op.add_column('users', sa.Column('hemis_data_hash', sa.String(64), nullable=True))
    op.add_column('users', sa.Column('hemis_last_synced_at',
                                     sa.DateTime(timezone=True), nullable=True))

    # Student-only fields
    op.add_column('users', sa.Column('group_id', sa.BigInteger(),
                                     sa.ForeignKey('academic_groups.id', ondelete='SET NULL'),
                                     nullable=True))
    op.create_index('ix_users_group_id', 'users', ['group_id'])
    op.add_column('users', sa.Column('current_semester_id', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('education_form', sa.String(20), nullable=True))
    op.add_column('users', sa.Column('payment_form', sa.String(20), nullable=True))
    op.add_column('users', sa.Column('student_status', sa.String(30), nullable=True))

    # Employee-only fields
    op.add_column('users', sa.Column('staff_position', sa.String(50), nullable=True))
    op.add_column('users', sa.Column('employment_form', sa.String(20), nullable=True))
    op.add_column('users', sa.Column('employment_staff', sa.String(20), nullable=True))


def downgrade() -> None:
    # Users — drop new columns
    op.drop_column('users', 'employment_staff')
    op.drop_column('users', 'employment_form')
    op.drop_column('users', 'staff_position')
    op.drop_column('users', 'student_status')
    op.drop_column('users', 'payment_form')
    op.drop_column('users', 'education_form')
    op.drop_column('users', 'current_semester_id')
    op.drop_index('ix_users_group_id', table_name='users')
    op.drop_column('users', 'group_id')
    op.drop_column('users', 'hemis_last_synced_at')
    op.drop_column('users', 'hemis_data_hash')
    op.drop_index('ix_users_hemis_login', table_name='users')
    op.drop_constraint('uq_users_hemis_login', 'users', type_='unique')
    op.drop_column('users', 'hemis_login')

    # email — qaytarib NOT NULL UNIQUE qilish
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ux_users_email_notnull', table_name='users')
    op.alter_column('users', 'email', nullable=False)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Profiles
    for col in ['academic_title', 'academic_degree', 'accommodation', 'poverty_level',
                'social_category', 'district', 'region', 'country',
                'middle_name', 'last_name', 'first_name']:
        op.drop_column('profiles', col)

    # Curricula
    op.drop_constraint('uq_curricula_hemis_id', 'curricula', type_='unique')
    op.drop_column('curricula', 'hemis_id')

    # Specialties
    op.drop_index('ix_specialties_hemis_code', table_name='specialties')
    op.drop_column('specialties', 'hemis_code')

    # Faculties
    op.drop_index('ix_faculties_hemis_id', table_name='faculties')
    op.drop_constraint('uq_faculties_hemis_id', 'faculties', type_='unique')
    for col in ['locality_type', 'structure_type', 'hemis_parent_id', 'hemis_code', 'hemis_id']:
        op.drop_column('faculties', col)

    op.drop_table('hemis_classifiers')
    op.drop_table('academic_semesters')
    op.drop_index('ix_academic_groups_specialty', table_name='academic_groups')
    op.drop_index('ix_academic_groups_faculty', table_name='academic_groups')
    op.drop_table('academic_groups')

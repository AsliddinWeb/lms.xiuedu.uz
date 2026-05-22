"""phase8c_composite_indices

Revision ID: 94e69c4d01f8
Revises: 7ad275b7020e
Create Date: 2026-05-19 14:00:00.000000

Phase 8c — Performance: tez-tez ishlatiladigan composite filtr'lar uchun
indekslar. Postgres bitta single-column index'larni kombinatsiya qila oladi,
lekin composite index'lar yana ham tezroq, ayniqsa katta jadvallar uchun.

Qo'shilayotgan indekslar:
  - ix_exam_attempts_exam_user      → (exam_id, user_id)
  - ix_exam_attempts_exam_status    → (exam_id, status)
  - ix_proctoring_events_attempt_at → (attempt_id, occurred_at)
  - ix_notifications_user_unread    → (user_id, read_at) — partial index
  - ix_submissions_assignment_user  → (assignment_id, user_id)
  - ix_courses_status_org           → (status, organization_id)
"""
from collections.abc import Sequence

from alembic import op


revision: str = '94e69c4d01f8'
down_revision: str | None = '7ad275b7020e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        'ix_exam_attempts_exam_user',
        'exam_attempts',
        ['exam_id', 'user_id'],
    )
    op.create_index(
        'ix_exam_attempts_exam_status',
        'exam_attempts',
        ['exam_id', 'status'],
    )
    op.create_index(
        'ix_proctoring_events_attempt_at',
        'exam_proctoring_events',
        ['attempt_id', 'occurred_at'],
    )
    # Partial index — faqat unread notifikatsiyalar uchun (eng ko'p so'rov)
    op.create_index(
        'ix_notifications_user_unread',
        'notifications',
        ['user_id', 'created_at'],
        postgresql_where=op.f("read_at IS NULL"),
    )
    op.create_index(
        'ix_submissions_assignment_user',
        'submissions',
        ['assignment_id', 'user_id'],
    )
    op.create_index(
        'ix_courses_status_org',
        'courses',
        ['status', 'organization_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_courses_status_org', table_name='courses')
    op.drop_index('ix_submissions_assignment_user', table_name='submissions')
    op.drop_index('ix_notifications_user_unread', table_name='notifications')
    op.drop_index(
        'ix_proctoring_events_attempt_at',
        table_name='exam_proctoring_events',
    )
    op.drop_index('ix_exam_attempts_exam_status', table_name='exam_attempts')
    op.drop_index('ix_exam_attempts_exam_user', table_name='exam_attempts')

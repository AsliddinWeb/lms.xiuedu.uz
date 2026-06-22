"""org.* permission nomlarini 'OTM' -> 'Universitet' qilish (bitta universitet)

Rollar katalogida permission nomlari ko'rinadi. Bitta universitet uchun 'OTM'
(ko'plik muassasa) atamasi noto'g'ri. Bu data-migration mavjud DB'dagi uchta
permission nomini yangilaydi (seed.py ham yangilangan — yangi DB'lar uchun).

Idempotent: kod bo'yicha WHERE filtrlanadi, qayta ishga tushsa zararsiz.

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-06-22
"""

from __future__ import annotations

from alembic import op

revision = "d5e6f7a8b9c0"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # asyncpg bitta prepared statement'da ko'p buyruqni qabul qilmaydi — alohida
    op.execute(
        "UPDATE permissions SET name = 'Universitet ko''rish' WHERE code = 'org.read'"
    )
    op.execute(
        "UPDATE permissions SET name = 'Universitet boshqarish' WHERE code = 'org.manage'"
    )
    op.execute(
        "UPDATE permissions SET name = 'Universitet foydalanuvchilarini boshqarish' "
        "WHERE code = 'org.users.manage'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE permissions SET name = 'OTM ko''rish' WHERE code = 'org.read'"
    )
    op.execute(
        "UPDATE permissions SET name = 'OTM boshqarish' WHERE code = 'org.manage'"
    )
    op.execute(
        "UPDATE permissions SET name = 'OTM foydalanuvchilarini boshqarish' "
        "WHERE code = 'org.users.manage'"
    )

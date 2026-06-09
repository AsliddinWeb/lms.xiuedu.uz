"""otm_admin rolini super_admin'ga birlashtirish (bitta universitet)

Bitta universitet uchun multi-tenant ajratish keraksiz. super_admin'ning
`platform.*` godmode wildcard'i hamma narsani avtomatik qoplaydi, shuning uchun
`otm_admin` rolini olib tashlaymiz va super_admin'ni "Administrator" deb
qayta nomlaymiz.

Migration idempotent: agar otm_admin allaqachon yo'q bo'lsa (lokal DB qo'lda
birlashtirilgan), barcha bandlar no-op bo'ladi.

Revision ID: c4d5e6f7a8b9
Revises: b2c3d4e5f6a7
Create Date: 2026-06-09
"""

from __future__ import annotations

from alembic import op

revision = "c4d5e6f7a8b9"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) otm_admin foydalanuvchilarini super_admin'ga ko'chirish (duplikatsiz)
    op.execute(
        """
        INSERT INTO user_roles (user_id, role_id, scope_type, scope_id, granted_by, granted_at, expires_at)
        SELECT ur.user_id, sa.id, ur.scope_type, ur.scope_id, ur.granted_by, ur.granted_at, ur.expires_at
        FROM user_roles ur
        JOIN roles otm ON otm.id = ur.role_id AND otm.code = 'otm_admin'
        CROSS JOIN roles sa
        WHERE sa.code = 'super_admin'
          AND NOT EXISTS (
            SELECT 1 FROM user_roles x WHERE x.user_id = ur.user_id AND x.role_id = sa.id
          );
        """
    )

    # 2) super_admin -> "Administrator"
    op.execute(
        """
        UPDATE roles
        SET name = 'Administrator',
            description = 'Universitetning barcha jarayonlarini boshqaradi (to''liq ruxsat)'
        WHERE code = 'super_admin';
        """
    )

    # 3) otm_admin rolini o'chirish (role_permissions + user_roles CASCADE bilan tozalanadi)
    op.execute("DELETE FROM roles WHERE code = 'otm_admin';")


def downgrade() -> None:
    # Eslatma: bu data-merge — DOWNGRADE LOSSY. super_admin nomi va otm_admin rol
    # qobig'i tiklanadi, LEKIN foydalanuvchi biriktiruvlari va otm_admin
    # permissionlari qayta tiklanmaydi (qaysi userlar otm_admin edi — ma'lum emas).
    op.execute(
        """
        UPDATE roles
        SET name = 'Super Administrator',
            description = 'Butun platformani boshqaradi (multi-tenant darajasida)'
        WHERE code = 'super_admin';
        """
    )
    op.execute(
        """
        INSERT INTO roles (code, name, description, is_system, created_at, updated_at)
        VALUES ('otm_admin', 'OTM Administratori', 'Bitta OTM doirasidagi barcha jarayonlar', true, now(), now())
        ON CONFLICT (code) DO NOTHING;
        """
    )

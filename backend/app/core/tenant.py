"""Single-tenant XIU helpers.

Loyiha faqat XIU (Xalqaro Innovatsiya Universiteti) uchun. Schema multi-tenant
strukturasini saqlaydi, lekin barcha record'lar yagona `Organization` (XIU)'ga
bog'lanadi. Bu modulda yagona organization'ni olish/yaratish uchun helperlar.

Tanlov: "Soft single-tenant" — schema o'zgarmaydi, faqat har joyda XIU id'si
ishlatiladi. Kelajakda ko'p universitet kerak bo'lsa, ushbu helperlarni yangilash
kifoya — ma'lumotlar saqlanib qoladi.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.organizations.models import Organization


async def get_xiu_org(db: AsyncSession) -> Organization:
    """XIU organization'ni qaytaradi (har doim mavjud — seed orqali yaratilgan).

    Raises:
        RuntimeError: agar XIU yaratilmagan bo'lsa (seed run qilinmagan).
    """
    stmt = select(Organization).where(Organization.code == settings.TENANT_CODE)
    org = (await db.execute(stmt)).scalar_one_or_none()
    if org is None:
        raise RuntimeError(
            f"XIU organization (code={settings.TENANT_CODE}) topilmadi — "
            "`python -m app.db.seed` ni ishga tushiring"
        )
    return org


async def get_xiu_org_id(db: AsyncSession) -> int:
    """XIU organization id'sini qaytaradi (yo'q bo'lsa avto-yaratiladi).

    Test fixture'larda Organization jadvali tozalanadi — har service
    chaqiruvi shu helper orqali XIU avto-tiklaydi (idempotent).
    """
    org = await ensure_xiu_org(db)
    return org.id


async def get_tenant_setting(
    db: AsyncSession, key: str, default: str | None = None
) -> str | None:
    """XIU `Organization.settings` JSONB'dan kalit qiymatini oladi.

    Misol: `await get_tenant_setting(db, "hemis.base_url", default=settings.HEMIS_API_URL)`

    Yo'lda `.` orqali nested kalitlar (`hemis.base_url` → `settings["hemis"]["base_url"]`).
    """
    org = await get_xiu_org(db)
    cur: object = org.settings or {}
    for part in key.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    if isinstance(cur, str):
        return cur
    return default


async def ensure_xiu_org(db: AsyncSession) -> Organization:
    """XIU organization mavjud bo'lmasa — yaratadi (idempotent).

    Faqat seed va migration backfill paytida ishlatiladi.
    """
    stmt = select(Organization).where(Organization.code == settings.TENANT_CODE)
    org = (await db.execute(stmt)).scalar_one_or_none()
    if org is not None:
        return org

    org = Organization(
        code=settings.TENANT_CODE,
        name=settings.TENANT_NAME,
        type="private",
        domain=settings.TENANT_DOMAIN,
        is_active=True,
        branding={},
        settings={},
    )
    db.add(org)
    await db.flush()
    return org

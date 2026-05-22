"""HEMIS SSO — talaba HEMIS login+parol bilan kiradi.

Phase 10d — qayta yozildi:
  - `upsert_student` (Phase 10b) ishlatiladi — barcha HEMIS field'lar to'liq sync
  - `HemisTokenCache` (Phase 10c) — keyingi HEMIS API chaqiruvlari uchun
  - Email endi optional (Phase 10b)

Flow:
  1. Foydalanuvchi HEMIS login (`student_id_number`) + parol yuboradi.
  2. Backend `HemisClient.student_login()` HEMIS'ga forward qiladi.
  3. HEMIS muvaffaqiyat → `account_me()` bilan to'liq profil olinadi.
  4. `upsert_student()` LMS user yaratadi/yangilaydi (hemis_id → hemis_login → pinfl).
  5. HEMIS JWT Redis cache'ga yoziladi (TTL 600s).
  6. Default `student` rol biriktiriladi (idempotent).
  7. LMS JWT chiqariladi.
"""

from __future__ import annotations

from datetime import UTC, datetime

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.hemis.client import (
    HemisAuthError,
    HemisClient,
    HemisError,
)
from app.integrations.hemis.token_cache import HemisTokenCache
from app.modules.auth.exceptions import AppException
from app.modules.auth.schemas import AuthContext, TokenResponse
from app.modules.auth.service import DEFAULT_REGISTER_ROLE, AuthService
from app.modules.rbac.models import Role, UserRole
from app.modules.users.hemis_sync import upsert_student, upsert_tutor
from app.modules.users.models import User


class HemisCredentialsError(AppException):
    def __init__(self, detail: str = "HEMIS rad qildi: login yoki parol noto'g'ri") -> None:
        from fastapi import status

        super().__init__(detail, status.HTTP_401_UNAUTHORIZED, "hemis_invalid_credentials")


class HemisUnreachableError(AppException):
    def __init__(self, detail: str = "HEMIS bilan ulanib bo'lmadi") -> None:
        from fastapi import status

        super().__init__(detail, status.HTTP_502_BAD_GATEWAY, "hemis_unreachable")


async def _ensure_role(db: AsyncSession, user: User, role_code: str) -> None:
    """Idempotent — `role_code` rolini biriktiradi (agar yo'q bo'lsa)."""
    result = await db.execute(select(Role).where(Role.code == role_code))
    role = result.scalar_one_or_none()
    if role is None:
        return
    existing = await db.execute(
        select(UserRole).where(
            UserRole.user_id == user.id,
            UserRole.role_id == role.id,
            UserRole.scope_type == "global",
        )
    )
    if existing.scalar_one_or_none() is not None:
        return
    db.add(UserRole(user_id=user.id, role_id=role.id, scope_type="global"))
    await db.flush()


async def _ensure_student_role(db: AsyncSession, user: User) -> None:
    """Backward-compat alias."""
    await _ensure_role(db, user, DEFAULT_REGISTER_ROLE)


async def _ensure_teacher_role(db: AsyncSession, user: User) -> None:
    """Phase 10g — HEMIS tutor login uchun 'teacher' rolini biriktiradi."""
    await _ensure_role(db, user, "teacher")


async def login_via_hemis_sso(
    db: AsyncSession,
    redis: Redis,
    *,
    sso_token: str,
    ctx: AuthContext,
) -> tuple[User, TokenResponse]:
    """Phase 10e — HEMIS SSO callback validation.

    Talaba HEMIS portalida login bo'lgan, "LMS'ga o'tish" tugmasini bossa,
    HEMIS bizga `?sso_token=...` bilan redirect qiladi. Biz tokenni HEMIS
    `/v1/account/me`-ga Bearer sifatida yuborib validate qilamiz va shu user
    uchun LMS JWT chiqaramiz.

    Steps:
        1. `HemisClient.account_me(sso_token)` — token validate + profil olish
        2. `upsert_student(student)` — User+Profile yaratish/yangilash
        3. `HemisTokenCache.set_student` — sso_token cache (qisqa muddat)
        4. Default `student` rolini biriktirish
        5. LMS JWT chiqarish

    Raises:
        HemisCredentialsError — sso_token yaroqsiz yoki muddati o'tgan
        HemisUnreachableError — HEMIS unreachable
    """
    from app.core.config import settings as app_settings
    from app.core.tenant import get_tenant_setting

    base_url = await get_tenant_setting(
        db, "hemis.base_url", default=app_settings.HEMIS_API_URL
    )

    try:
        async with HemisClient(base_url=base_url) as client:
            student = await client.account_me(sso_token)
    except HemisAuthError as exc:
        # SSO token yaroqsiz/expire (HEMIS 401 qaytarsa)
        raise HemisCredentialsError(
            f"HEMIS SSO token yaroqsiz yoki muddati o'tgan: {exc}"
        ) from exc
    except HemisError as exc:
        raise HemisUnreachableError(f"HEMIS bilan ulanib bo'lmadi: {exc}") from exc

    user = await upsert_student(db, student)
    await _ensure_student_role(db, user)

    # SSO token cache — keyingi 5 daqiqada qayta validate kerakmas
    cache = HemisTokenCache(redis)
    await cache.set_student(user.id, sso_token, refresh=None)

    user.last_login_at = datetime.now(UTC)
    user.last_login_ip = ctx.ip_address
    auth_service = AuthService(db, redis)
    token_response = await auth_service._issue_tokens(user, ctx)
    return user, token_response


async def login_via_hemis(
    db: AsyncSession,
    redis: Redis,
    *,
    hemis_login: str,
    hemis_password: str,
    ctx: AuthContext,
) -> tuple[User, TokenResponse]:
    """End-to-end HEMIS SSO — Phase 10d refactor.

    Steps:
        1. HemisClient.student_login → JWT
        2. HemisClient.account_me → full student profile
        3. upsert_student → User+Profile (idempotent, hash-based)
        4. HemisTokenCache.set_student → keyingi sync uchun
        5. Ensure student role
        6. Issue LMS JWT
    """
    # Single-tenant XIU: base_url'ni Organization.settings.hemis.base_url'dan o'qiymiz
    from app.core.config import settings as app_settings
    from app.core.tenant import get_tenant_setting

    base_url = await get_tenant_setting(
        db, "hemis.base_url", default=app_settings.HEMIS_API_URL
    )

    try:
        async with HemisClient(base_url=base_url) as client:
            tokens = await client.student_login(hemis_login, hemis_password)
            student = await client.account_me(tokens["token"])
    except HemisAuthError as exc:
        msg = str(exc)
        if "HEMIS" not in msg:
            msg = f"HEMIS rad qildi: {msg}"
        raise HemisCredentialsError(msg) from exc
    except HemisError as exc:
        raise HemisUnreachableError(f"HEMIS bilan ulanib bo'lmadi: {exc}") from exc

    # Phase 10b — upsert_student barcha HEMIS field'larni sync qiladi
    user = await upsert_student(db, student)
    await _ensure_student_role(db, user)

    # Phase 10c — HEMIS JWT Redis'ga keyingi sync chaqiruvlari uchun
    cache = HemisTokenCache(redis)
    await cache.set_student(
        user.id, tokens["token"], refresh=tokens.get("refresh_token")
    )

    # Lokal JWT chiqarish
    user.last_login_at = datetime.now(UTC)
    user.last_login_ip = ctx.ip_address
    auth_service = AuthService(db, redis)
    token_response = await auth_service._issue_tokens(user, ctx)
    return user, token_response


async def login_via_hemis_tutor(
    db: AsyncSession,
    redis: Redis,
    *,
    tutor_login: str,
    tutor_password: str,
    recaptcha: str,
    ctx: AuthContext,
) -> tuple[User, TokenResponse]:
    """Phase 10g — Pedagog HEMIS login (`/ver1/tutor/auth/login`).

    Steps:
        1. HemisClient.tutor_login(login, password, recaptcha) → JWT + refresh
        2. HemisClient.tutor_profile(token) → pedagog profil
        3. upsert_tutor(profile) → User+Profile
        4. Ensure 'teacher' role
        5. HemisTokenCache.set_tutor → keyingi tutor API chaqiruvlari uchun
        6. LMS JWT chiqarish

    reCAPTCHA validation HEMIS tomonida amalga oshiriladi — biz frontend'dan
    olib HEMIS'ga forward qilamiz.
    """
    from app.core.config import settings as app_settings
    from app.core.tenant import get_tenant_setting

    base_url = await get_tenant_setting(
        db, "hemis.base_url", default=app_settings.HEMIS_API_URL
    )

    try:
        async with HemisClient(base_url=base_url) as client:
            tokens = await client.tutor_login(tutor_login, tutor_password, recaptcha)
            profile = await client.tutor_profile(tokens["token"])
    except HemisAuthError as exc:
        msg = str(exc)
        if "HEMIS" not in msg:
            msg = f"HEMIS rad qildi: {msg}"
        raise HemisCredentialsError(msg) from exc
    except HemisError as exc:
        raise HemisUnreachableError(f"HEMIS bilan ulanib bo'lmadi: {exc}") from exc

    user = await upsert_tutor(db, profile)
    await _ensure_teacher_role(db, user)

    # Tutor JWT cache — keyingi /tutor/* API chaqiruvlari uchun
    cache = HemisTokenCache(redis)
    await cache.set_tutor(
        user.id, tokens["token"], refresh=tokens.get("refresh_token")
    )

    user.last_login_at = datetime.now(UTC)
    user.last_login_ip = ctx.ip_address
    auth_service = AuthService(db, redis)
    token_response = await auth_service._issue_tokens(user, ctx)
    return user, token_response

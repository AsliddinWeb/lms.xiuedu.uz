"""HEMIS OAuth2 standart oqim — Phase 15.

Django namuna (`md_files/oAuth2-by-hemis-master`) asosida:
    1. Talaba/o'qituvchi LMS'da "HEMIS orqali kirish" bossa
    2. Backend authorize URL yasaydi (state CSRF token bilan) → frontend redirect
    3. Foydalanuvchi HEMIS portalida login qiladi
    4. HEMIS bizning `redirect_uri`'ga `?code=...&state=...` bilan qaytadi
    5. Frontend code+state'ni backend'ga POST qiladi
    6. Backend code → access_token (HEMIS token endpoint)
    7. Backend access_token → user info (HEMIS resource owner endpoint)
    8. User upsert (talaba — `upsert_student`, xodim — `upsert_employee`)
    9. LMS JWT chiqariladi
"""

from __future__ import annotations

import secrets
from typing import Any, Literal
from urllib.parse import urlencode

import httpx
from redis.asyncio import Redis

from app.core.config import settings
from app.core.exceptions import UnauthorizedError, ValidationError
from app.core.logging import get_logger

logger = get_logger(__name__)

OAuthRole = Literal["student", "employee"]
_STATE_PREFIX = "hemis_oauth_state:"


# ============================================================================
# State (CSRF) — Redis'da TTL bilan saqlanadi
# ============================================================================


def _new_state() -> str:
    """URL-safe random 32 belgi."""
    return secrets.token_urlsafe(24)


async def issue_state(redis: Redis, role: OAuthRole) -> str:
    """Yangi state token yaratib, role bilan birga Redis'ga TTL bilan saqlash."""
    state = _new_state()
    key = _STATE_PREFIX + state
    await redis.setex(key, settings.HEMIS_OAUTH_STATE_TTL, role)
    return state


async def consume_state(redis: Redis, state: str) -> OAuthRole:
    """State'ni Redis'dan o'qib, darhol o'chiradi (one-time use)."""
    if not state:
        raise ValidationError("state mavjud emas")
    key = _STATE_PREFIX + state
    role = await redis.get(key)
    if role is None:
        raise UnauthorizedError("state noto'g'ri yoki muddati tugagan")
    await redis.delete(key)
    if role not in ("student", "employee"):
        raise UnauthorizedError("state'da noma'lum rol")
    return role  # type: ignore[return-value]


# ============================================================================
# URL builder
# ============================================================================


def _urls_for(role: OAuthRole) -> tuple[str, str, str]:
    """Role'ga qarab (authorize_url, token_url, userinfo_url) qaytaradi."""
    if role == "student":
        return (
            settings.HEMIS_OAUTH_STUDENT_AUTHORIZE_URL,
            settings.HEMIS_OAUTH_STUDENT_TOKEN_URL,
            settings.HEMIS_OAUTH_STUDENT_USERINFO_URL,
        )
    return (
        settings.HEMIS_OAUTH_EMPLOYEE_AUTHORIZE_URL,
        settings.HEMIS_OAUTH_EMPLOYEE_TOKEN_URL,
        settings.HEMIS_OAUTH_EMPLOYEE_USERINFO_URL,
    )


def build_authorize_url(role: OAuthRole, state: str) -> str:
    """HEMIS authorize URL'ini yasaydi.

    Django namunadagidek: client_id, client_secret, redirect_uri, response_type=code, state.
    """
    authorize_url, _, _ = _urls_for(role)
    if not authorize_url:
        raise ValidationError(
            f"HEMIS_OAUTH_{role.upper()}_AUTHORIZE_URL sozlanmagan"
        )
    if not settings.HEMIS_OAUTH_CLIENT_ID or not settings.HEMIS_OAUTH_REDIRECT_URI:
        raise ValidationError(
            "HEMIS_OAUTH_CLIENT_ID yoki HEMIS_OAUTH_REDIRECT_URI sozlanmagan"
        )
    payload = {
        "client_id": settings.HEMIS_OAUTH_CLIENT_ID,
        "client_secret": settings.HEMIS_OAUTH_CLIENT_SECRET,
        "redirect_uri": settings.HEMIS_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "state": state,
    }
    return f"{authorize_url}?{urlencode(payload)}"


# ============================================================================
# Token exchange + userinfo
# ============================================================================


async def exchange_code(
    role: OAuthRole, code: str
) -> dict[str, Any]:
    """HEMIS token endpoint'ga `code` yuborib `access_token` oladi."""
    _, token_url, _ = _urls_for(role)
    if not token_url:
        raise ValidationError(
            f"HEMIS_OAUTH_{role.upper()}_TOKEN_URL sozlanmagan"
        )
    payload = {
        "client_id": settings.HEMIS_OAUTH_CLIENT_ID,
        "client_secret": settings.HEMIS_OAUTH_CLIENT_SECRET,
        "code": code,
        "redirect_uri": settings.HEMIS_OAUTH_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(token_url, data=payload)
    if r.status_code != 200:
        logger.warning(
            "hemis_oauth.token_failed",
            role=role,
            status=r.status_code,
            body=r.text[:300],
        )
        raise UnauthorizedError(
            f"HEMIS access_token olishda xato (HTTP {r.status_code})"
        )
    data = r.json()
    if "access_token" not in data:
        logger.warning("hemis_oauth.no_access_token", role=role, response=data)
        raise UnauthorizedError("HEMIS access_token qaytarmadi")
    return data


async def fetch_userinfo(
    role: OAuthRole, access_token: str
) -> dict[str, Any]:
    """HEMIS resource owner endpoint'dan user ma'lumotlarini olish."""
    _, _, userinfo_url = _urls_for(role)
    if not userinfo_url:
        raise ValidationError(
            f"HEMIS_OAUTH_{role.upper()}_USERINFO_URL sozlanmagan"
        )
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(
            userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if r.status_code != 200:
        logger.warning(
            "hemis_oauth.userinfo_failed",
            role=role,
            status=r.status_code,
        )
        raise UnauthorizedError(
            f"HEMIS user info olishda xato (HTTP {r.status_code})"
        )
    return r.json()


# ============================================================================
# Full login flow — code -> user upsert -> JWT
# ============================================================================


async def login_via_oauth(
    db,  # type: ignore[no-untyped-def]
    redis: Redis,
    *,
    code: str,
    state: str,
    ctx,  # type: ignore[no-untyped-def]
):
    """End-to-end OAuth oqimi.

    1. state validate (Redis'dan role olinadi)
    2. code -> access_token
    3. access_token -> userinfo
    4. role'ga qarab upsert_student yoki upsert_employee
    5. Tegishli rolni ulash
    6. LMS JWT chiqarish
    """
    from datetime import UTC, datetime

    from app.modules.auth.hemis_login import (
        _ensure_student_role,
        _ensure_teacher_role,
    )
    from app.modules.auth.service import AuthService
    from app.modules.users.hemis_sync import upsert_employee, upsert_student

    role = await consume_state(redis, state)

    token_data = await exchange_code(role, code)
    access_token = token_data["access_token"]
    user_data = await fetch_userinfo(role, access_token)

    if role == "student":
        user = await upsert_student(db, user_data)
        await _ensure_student_role(db, user)
    else:
        user = await upsert_employee(db, user_data)
        await _ensure_teacher_role(db, user)

    user.last_login_at = datetime.now(UTC)
    user.last_login_ip = ctx.ip_address
    auth_service = AuthService(db, redis)
    token_response = await auth_service._issue_tokens(user, ctx)
    return user, token_response

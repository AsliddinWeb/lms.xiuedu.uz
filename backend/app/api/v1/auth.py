"""Auth endpoint'lari: register, login, refresh, logout, me, sessions.

Spec: docs/03-modules/01-auth.md
"""

from __future__ import annotations

import base64

from fastapi import APIRouter, Response, status
from sqlalchemy import desc, select

from app.core.config import settings
from app.core.exceptions import ForbiddenError
from app.core.security import hash_password, verify_password
from app.modules.auth import tokens as token_service
from app.modules.auth import two_factor
from app.modules.auth.dependencies import (
    CurrentUser,
    DbSession,
    RedisClient,
    ReqContext,
)
from app.modules.auth.exceptions import InvalidCredentialsError, InvalidTotpError
from app.modules.auth.hemis_login import (
    login_via_hemis,
    login_via_hemis_sso,
    login_via_hemis_tutor,
)
from app.modules.auth.hemis_oauth import (
    build_authorize_url,
    issue_state,
    login_via_oauth,
)
from app.modules.auth.models import UserSession
from app.modules.auth.schemas import (
    BackupCodesResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    HemisLoginRequest,
    HemisSsoCallbackRequest,
    HemisTutorLoginRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SessionPublic,
    TokenResponse,
    TwoFactorDisableRequest,
    TwoFactorEnableResponse,
    TwoFactorSetupResponse,
    TwoFactorVerifyRequest,
    UserPublic,
    VerifyEmailRequest,
)
from app.modules.auth.service import AuthService
from app.modules.email.service import send_email_verification, send_password_reset
from app.modules.rbac.service import RBACService

router = APIRouter()


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Refresh token'ni HttpOnly cookie sifatida yuborish (4-domain arxitektura uchun)."""
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN or None,
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key="refresh_token",
        domain=settings.COOKIE_DOMAIN or None,
        path="/",
    )


# -----------------------------------------------------------------------------


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi foydalanuvchi (talaba) ro'yxatdan o'tkazish",
)
async def register(
    data: RegisterRequest, ctx: ReqContext, db: DbSession, redis: RedisClient
) -> UserPublic:
    service = AuthService(db, redis)
    user = await service.register(data, ctx)

    # Email verification token + email yuborish
    raw = await token_service.issue_email_verification_token(db, user)
    await db.commit()

    verify_url = f"{settings.APP_FRONTEND_URL}/verify-email?token={raw}"
    await send_email_verification(
        to=user.email, full_name=user.full_name, verify_url=verify_url
    )

    return UserPublic(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_2fa_enabled=user.is_2fa_enabled,
        last_login_at=user.last_login_at,
        tenant_id=user.tenant_id,
        roles=[],
        permissions=[],
    )


@router.post("/login", response_model=TokenResponse, summary="Email + parol bilan kirish")
async def login(
    data: LoginRequest,
    response: Response,
    ctx: ReqContext,
    db: DbSession,
    redis: RedisClient,
) -> TokenResponse:
    service = AuthService(db, redis)
    _user, tokens = await service.login(data, ctx)
    await db.commit()
    _set_refresh_cookie(response, tokens.refresh_token)
    return tokens


@router.post(
    "/login/hemis",
    response_model=TokenResponse,
    summary="HEMIS proxy — talaba HEMIS login+parol bilan kiradi",
)
async def login_hemis(
    data: HemisLoginRequest,
    response: Response,
    ctx: ReqContext,
    db: DbSession,
    redis: RedisClient,
) -> TokenResponse:
    _user, tokens = await login_via_hemis(
        db,
        redis,
        hemis_login=data.login,
        hemis_password=data.password,
        ctx=ctx,
    )
    await db.commit()
    _set_refresh_cookie(response, tokens.refresh_token)
    return tokens


@router.post(
    "/login/hemis-tutor",
    response_model=TokenResponse,
    summary="HEMIS Tutor proxy — pedagog HEMIS login+parol+reCAPTCHA bilan kiradi",
)
async def login_hemis_tutor(
    data: HemisTutorLoginRequest,
    response: Response,
    ctx: ReqContext,
    db: DbSession,
    redis: RedisClient,
) -> TokenResponse:
    """Phase 10g — Pedagog HEMIS login.

    Talaba flow'idan farqlar:
        - reCAPTCHA majburiy (Google reCAPTCHA v3 token frontend tomonida olinadi)
        - HEMIS tutor endpoint: `/ver1/tutor/auth/login`
        - Bizning user'ga 'teacher' role biriktiriladi (student emas)
        - Tutor JWT alohida Redis cache namespace'da saqlanadi
    """
    _user, tokens = await login_via_hemis_tutor(
        db,
        redis,
        tutor_login=data.login,
        tutor_password=data.password,
        recaptcha=data.recaptcha,
        ctx=ctx,
    )
    await db.commit()
    _set_refresh_cookie(response, tokens.refresh_token)
    return tokens


@router.get(
    "/hemis/oauth/start",
    summary="HEMIS OAuth2 boshlash — authorize URL qaytaradi",
)
async def hemis_oauth_start(
    role: str,
    redis: RedisClient,
) -> dict:
    """Phase 15 — Standart OAuth2 oqimi boshlanishi.

    `role=student` yoki `role=employee` bilan chaqiriladi.
    Backend Redis'da state CSRF token saqlab, HEMIS authorize URL qaytaradi.
    Frontend window.location.href = URL qiladi.
    """
    if role not in ("student", "employee"):
        raise ForbiddenError("role 'student' yoki 'employee' bo'lishi kerak")
    state = await issue_state(redis, role)
    url = build_authorize_url(role, state)
    return {"authorize_url": url, "state": state}


from pydantic import BaseModel


class HemisOAuthCallbackRequest(BaseModel):
    """Code va state — frontend `?code=...&state=...` ni POST qiladi."""

    code: str
    state: str


@router.post(
    "/hemis/oauth/callback",
    response_model=TokenResponse,
    summary="HEMIS OAuth2 callback — code/state validate va LMS JWT",
)
async def hemis_oauth_callback(
    data: HemisOAuthCallbackRequest,
    response: Response,
    ctx: ReqContext,
    db: DbSession,
    redis: RedisClient,
) -> TokenResponse:
    """Phase 15 — HEMIS code -> access_token -> userinfo -> LMS JWT."""
    _user, tokens = await login_via_oauth(
        db, redis, code=data.code, state=data.state, ctx=ctx
    )
    await db.commit()
    _set_refresh_cookie(response, tokens.refresh_token)
    return tokens


@router.post(
    "/sso/hemis",
    response_model=TokenResponse,
    summary="HEMIS SSO callback — sso_token validate va LMS JWT chiqarish",
)
async def sso_hemis(
    data: HemisSsoCallbackRequest,
    response: Response,
    ctx: ReqContext,
    db: DbSession,
    redis: RedisClient,
) -> TokenResponse:
    """Phase 10e — HEMIS SSO callback handler.

    Flow:
        1. Talaba HEMIS portalida login bo'lib turibdi
        2. HEMIS portalda "LMS'ga o'tish" tugmasi → HEMIS
           `GET /v1/sso/get-redirect-url?target=lms` chaqiradi
        3. HEMIS bizga 302 redirect: `https://lms.xiuedu.uz/auth/sso/callback?sso_token=...`
        4. Frontend callback view sso_token-ni shu endpointga POST qiladi
        5. Backend HEMIS-ga `/v1/account/me` (sso_token bilan) chaqirib validate
        6. User upsert + LMS JWT chiqariladi

    Token muddati: 300 sekund (HEMIS taqdim etadi).
    """
    _user, tokens = await login_via_hemis_sso(
        db, redis, sso_token=data.sso_token, ctx=ctx
    )
    await db.commit()
    _set_refresh_cookie(response, tokens.refresh_token)
    return tokens


@router.post("/refresh", response_model=TokenResponse, summary="Tokenni yangilash (rotation)")
async def refresh(
    data: RefreshRequest,
    response: Response,
    ctx: ReqContext,
    db: DbSession,
    redis: RedisClient,
) -> TokenResponse:
    service = AuthService(db, redis)
    tokens = await service.refresh(data.refresh_token, ctx)
    await db.commit()
    _set_refresh_cookie(response, tokens.refresh_token)
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Joriy sessiyadan chiqish")
async def logout(
    data: RefreshRequest, response: Response, db: DbSession, redis: RedisClient
) -> Response:
    service = AuthService(db, redis)
    await service.logout(data.refresh_token)
    await db.commit()
    _clear_refresh_cookie(response)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/logout-all",
    summary="Barcha qurilmalardan chiqish",
)
async def logout_all(
    user: CurrentUser, response: Response, db: DbSession, redis: RedisClient
) -> dict[str, int]:
    service = AuthService(db, redis)
    revoked = await service.logout_all(user.id)
    await db.commit()
    _clear_refresh_cookie(response)
    return {"revoked_sessions": revoked}


@router.get("/me", response_model=UserPublic, summary="Joriy foydalanuvchi profili")
async def me(user: CurrentUser, db: DbSession, redis: RedisClient) -> UserPublic:
    rbac = RBACService(db, redis)
    roles = await rbac.get_user_roles(user.id)
    perms = await rbac.get_user_permissions(user.id)
    return UserPublic(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_2fa_enabled=user.is_2fa_enabled,
        last_login_at=user.last_login_at,
        tenant_id=user.tenant_id,
        roles=roles,
        permissions=perms,
    )


@router.get("/sessions", response_model=list[SessionPublic], summary="Faol sessiyalar")
async def list_sessions(user: CurrentUser, db: DbSession) -> list[SessionPublic]:
    stmt = (
        select(UserSession)
        .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        .order_by(desc(UserSession.created_at))
    )
    result = await db.execute(stmt)
    return [SessionPublic.model_validate(s) for s in result.scalars().all()]


# =============================================================================
# Forgot / Reset password
# =============================================================================


@router.post(
    "/forgot-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Parolni tiklash so'rovi (email yuboriladi)",
)
async def forgot_password(data: ForgotPasswordRequest, db: DbSession) -> Response:
    """Email mavjud bo'lsa email yuboradi.
    Foydalanuvchi mavjud yo'qligini fosh qilmaslik uchun har holatda 204 qaytaramiz."""
    from app.modules.users.models import User

    stmt = select(User).where(
        User.email == data.email.lower().strip(), User.deleted_at.is_(None)
    )
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is not None and user.is_active:
        raw = await token_service.issue_password_reset_token(db, user)
        await db.commit()
        reset_url = f"{settings.APP_FRONTEND_URL}/reset-password?token={raw}"
        await send_password_reset(to=user.email, full_name=user.full_name, reset_url=reset_url)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Tokenni ishlatib parolni o'zgartirish",
)
async def reset_password(data: ResetPasswordRequest, db: DbSession) -> Response:
    user = await token_service.consume_password_reset_token(db, data.token)
    user.password_hash = hash_password(data.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Joriy foydalanuvchi o'z parolini o'zgartirish",
)
async def change_password(
    data: ChangePasswordRequest, user: CurrentUser, db: DbSession
) -> Response:
    if not user.password_hash or not verify_password(data.old_password, user.password_hash):
        raise InvalidCredentialsError()
    user.password_hash = hash_password(data.new_password)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =============================================================================
# Email verification
# =============================================================================


@router.post(
    "/verify-email",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Email tasdiqlash (token orqali)",
)
async def verify_email(data: VerifyEmailRequest, db: DbSession) -> Response:
    await token_service.consume_email_verification_token(db, data.token)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/resend-verification",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Email tasdiqlash xatini qayta yuborish",
)
async def resend_verification(user: CurrentUser, db: DbSession) -> Response:
    if user.is_verified:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    raw = await token_service.issue_email_verification_token(db, user)
    await db.commit()
    verify_url = f"{settings.APP_FRONTEND_URL}/verify-email?token={raw}"
    await send_email_verification(
        to=user.email, full_name=user.full_name, verify_url=verify_url
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =============================================================================
# 2FA TOTP
# =============================================================================


@router.post(
    "/2fa/setup",
    response_model=TwoFactorSetupResponse,
    summary="2FA secret + QR yaratish (faollashtirilmagan holatda)",
)
async def setup_2fa(user: CurrentUser, db: DbSession) -> TwoFactorSetupResponse:
    secret = two_factor.generate_secret()
    user.totp_secret = secret  # hali yoqilmagan, faqat verify'dan so'ng yoqamiz
    await db.commit()

    uri = two_factor.provisioning_uri(secret=secret, account_name=user.email)
    png = two_factor.make_qr_png(uri)
    return TwoFactorSetupResponse(
        secret=secret,
        otpauth_uri=uri,
        qr_png_base64=base64.b64encode(png).decode("ascii"),
    )


@router.post(
    "/2fa/enable",
    response_model=TwoFactorEnableResponse,
    summary="Setup so'ngida TOTP'ni tasdiqlab 2FA'ni yoqish",
)
async def enable_2fa(
    data: TwoFactorVerifyRequest, user: CurrentUser, db: DbSession
) -> TwoFactorEnableResponse:
    if not user.totp_secret:
        raise ForbiddenError("Avval 2FA setup'ni boshlang")
    if not two_factor.verify_totp(user.totp_secret, data.code):
        raise InvalidTotpError()

    user.is_2fa_enabled = True
    raw_codes = await two_factor.regenerate_backup_codes(db, user)
    await db.commit()
    return TwoFactorEnableResponse(backup_codes=raw_codes)


@router.post(
    "/2fa/disable",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Parol + TOTP bilan 2FA'ni o'chirish",
)
async def disable_2fa_endpoint(
    data: TwoFactorDisableRequest, user: CurrentUser, db: DbSession
) -> Response:
    if not user.is_2fa_enabled:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    # TOTP tasdiqlash (yoki backup code)
    if not await two_factor.verify_totp_or_backup(db, user, data.code):
        raise InvalidTotpError()
    await two_factor.disable_2fa(db, user, password=data.password)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/2fa/backup-codes/regenerate",
    response_model=BackupCodesResponse,
    summary="Backup codelarni qayta yaratish",
)
async def regenerate_backup_codes(
    user: CurrentUser, db: DbSession
) -> BackupCodesResponse:
    if not user.is_2fa_enabled:
        raise ForbiddenError("2FA yoqilmagan")
    raw_codes = await two_factor.regenerate_backup_codes(db, user)
    await db.commit()
    return BackupCodesResponse(backup_codes=raw_codes)

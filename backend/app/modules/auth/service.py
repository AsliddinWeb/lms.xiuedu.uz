"""Auth servisi — register / login / refresh / logout / sessionlar.

Spec: docs/03-modules/01-auth.md
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.modules.auth import rate_limit, two_factor
from app.modules.auth.exceptions import (
    AccountDisabledError,
    InvalidCredentialsError,
    InvalidTokenError,
    InvalidTotpError,
    SessionRevokedError,
    TwoFactorRequiredError,
    UserAlreadyExistsError,
)
from app.modules.auth.models import LoginAttempt, UserSession
from app.modules.auth.schemas import (
    AuthContext,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.modules.rbac.models import Role, UserRole
from app.modules.rbac.service import RBACService
from app.modules.users.models import Profile, User

DEFAULT_REGISTER_ROLE = "student"


def _now() -> datetime:
    return datetime.now(UTC)


class AuthService:
    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self.db = db
        self.redis = redis

    # ---------------------------------------------------------------
    # Register
    # ---------------------------------------------------------------

    async def register(self, data: RegisterRequest, ctx: AuthContext) -> User:
        existing = await self._get_by_email(data.email)
        if existing:
            raise UserAlreadyExistsError()

        user = User(
            email=data.email.lower().strip(),
            phone=data.phone,
            password_hash=hash_password(data.password),
            full_name=data.full_name.strip(),
            is_active=True,
            is_verified=False,
        )
        user.profile = Profile()
        self.db.add(user)
        await self.db.flush()

        # Default rolni biriktirish (talaba)
        result = await self.db.execute(select(Role).where(Role.code == DEFAULT_REGISTER_ROLE))
        default_role = result.scalar_one_or_none()
        if default_role is not None:
            self.db.add(
                UserRole(user_id=user.id, role_id=default_role.id, scope_type="global")
            )
            await self.db.flush()

        await self.db.refresh(user)
        return user

    # ---------------------------------------------------------------
    # Login
    # ---------------------------------------------------------------

    async def login(self, data: LoginRequest, ctx: AuthContext) -> tuple[User, TokenResponse]:
        ident = data.email or data.phone
        if not ident:
            raise InvalidCredentialsError()

        await rate_limit.assert_not_locked(self.redis, ip=ctx.ip_address, email=data.email)

        user = await self._get_by_email_or_phone(data.email, data.phone)
        if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
            await self._record_attempt(ident, None, ctx, success=False, reason="invalid_credentials")
            await rate_limit.record_failed_attempt(self.redis, ip=ctx.ip_address, email=data.email)
            raise InvalidCredentialsError()

        if not user.is_active or user.deleted_at is not None:
            await self._record_attempt(ident, user.id, ctx, success=False, reason="account_disabled")
            raise AccountDisabledError()

        if user.is_2fa_enabled:
            if not data.totp_code:
                raise TwoFactorRequiredError()
            ok = await two_factor.verify_totp_or_backup(self.db, user, data.totp_code)
            if not ok:
                await self._record_attempt(
                    ident, user.id, ctx, success=False, reason="invalid_totp"
                )
                raise InvalidTotpError()

        # Muvaffaqiyatli login
        await rate_limit.reset_attempts(self.redis, ip=ctx.ip_address, email=data.email)
        await self._record_attempt(ident, user.id, ctx, success=True)

        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = _now()
        user.last_login_ip = ctx.ip_address

        tokens = await self._issue_tokens(user, ctx)
        return user, tokens

    # ---------------------------------------------------------------
    # Refresh
    # ---------------------------------------------------------------

    async def refresh(self, refresh_token: str, ctx: AuthContext) -> TokenResponse:
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
        except ValueError as exc:
            raise InvalidTokenError(str(exc)) from exc

        user_id = int(payload["sub"])
        token_h = hash_token(refresh_token)

        session = await self._get_session_by_token_hash(token_h)
        if session is None:
            raise InvalidTokenError("Sessiya topilmadi")
        if session.revoked_at is not None:
            raise SessionRevokedError()
        if session.expires_at < _now():
            raise InvalidTokenError("Refresh token muddati o'tgan")
        if session.user_id != user_id:
            raise InvalidTokenError("Token foydalanuvchiga mos kelmaydi")

        # Token rotation — eski sessiyani revoke, yangisini yaratish
        session.revoked_at = _now()

        user = await self.db.get(User, user_id)
        if not user or not user.is_active:
            raise AccountDisabledError()

        return await self._issue_tokens(user, ctx)

    # ---------------------------------------------------------------
    # Logout
    # ---------------------------------------------------------------

    async def logout(self, refresh_token: str) -> None:
        try:
            decode_token(refresh_token, expected_type="refresh")
        except ValueError:
            return  # Yaroqsiz token — sukut bilan chiqib ketamiz
        token_h = hash_token(refresh_token)
        session = await self._get_session_by_token_hash(token_h)
        if session and session.revoked_at is None:
            session.revoked_at = _now()

    async def logout_all(self, user_id: int) -> int:
        stmt = select(UserSession).where(
            UserSession.user_id == user_id, UserSession.revoked_at.is_(None)
        )
        result = await self.db.execute(stmt)
        sessions = result.scalars().all()
        now = _now()
        for s in sessions:
            s.revoked_at = now
        return len(sessions)

    # ---------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------

    async def _issue_tokens(self, user: User, ctx: AuthContext) -> TokenResponse:
        rbac = RBACService(self.db, self.redis)
        roles = await rbac.get_user_roles(user.id)
        access = create_access_token(
            user.id,
            extra_claims={
                "email": user.email,
                "tenant_id": user.tenant_id,
                "roles": roles,
            },
        )
        refresh = create_refresh_token(user.id)

        session = UserSession(
            user_id=user.id,
            refresh_token_hash=hash_token(refresh),
            ip_address=ctx.ip_address,
            user_agent=ctx.user_agent,
            device_info={},
            expires_at=_now() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
            last_used_at=_now(),
        )
        self.db.add(session)
        await self.db.flush()

        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def _get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower().strip(), User.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_by_email_or_phone(self, email: str | None, phone: str | None) -> User | None:
        if email:
            return await self._get_by_email(email)
        if phone:
            stmt = select(User).where(User.phone == phone, User.deleted_at.is_(None))
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        return None

    # Phase 10b — HEMIS-first lookup
    async def get_by_hemis_id(self, hemis_id: int) -> User | None:
        stmt = select(User).where(
            User.hemis_id == hemis_id, User.deleted_at.is_(None)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_by_hemis_login(self, hemis_login: str) -> User | None:
        stmt = select(User).where(
            User.hemis_login == hemis_login.strip(), User.deleted_at.is_(None)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_by_identifier(
        self, identifier: str
    ) -> User | None:
        """Universal lookup — email, hemis_login, yoki phone.

        Tartibi:
            1. Email format (@-belgisi bor) → email lookup
            2. Faqat raqamlar (telefon yoki HEMIS login) → ikkala variant
            3. Boshqa string → hemis_login

        Phase 10b — HEMIS login eng yuqori prioritetda raqamli identifierlar uchun.
        """
        ident = identifier.strip()
        if not ident:
            return None
        # Email
        if "@" in ident:
            return await self._get_by_email(ident)
        # Raqamli (HEMIS login odatda 12 raqamli, telefon +998..)
        if ident.replace("+", "").isdigit():
            # Avval HEMIS login, keyin phone
            user = await self.get_by_hemis_login(ident)
            if user:
                return user
            stmt = select(User).where(User.phone == ident, User.deleted_at.is_(None))
            return (await self.db.execute(stmt)).scalar_one_or_none()
        # Boshqa string
        return await self.get_by_hemis_login(ident)

    async def _get_session_by_token_hash(self, token_hash: str) -> UserSession | None:
        stmt = select(UserSession).where(UserSession.refresh_token_hash == token_hash)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _record_attempt(
        self,
        email_or_phone: str,
        user_id: int | None,
        ctx: AuthContext,
        *,
        success: bool,
        reason: str | None = None,
    ) -> None:
        attempt = LoginAttempt(
            email=email_or_phone if "@" in email_or_phone else None,
            user_id=user_id,
            ip_address=ctx.ip_address,
            user_agent=ctx.user_agent,
            success=success,
            failure_reason=reason,
        )
        self.db.add(attempt)

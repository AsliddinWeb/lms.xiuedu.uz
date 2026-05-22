"""Bir martalik token'lar (parol tiklash + email tasdiqlash) servisi.

Token'ning RAW qiymati emailda yuboriladi, DB'da SHA-256 hash sifatida saqlanadi.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_url_token, hash_token
from app.modules.auth.exceptions import InvalidTokenError
from app.modules.auth.models import EmailVerificationToken, PasswordResetToken
from app.modules.users.models import User

PASSWORD_RESET_TTL = timedelta(hours=1)
EMAIL_VERIFICATION_TTL = timedelta(hours=24)


def _now() -> datetime:
    return datetime.now(UTC)


# ---------- Password reset ----------


async def issue_password_reset_token(db: AsyncSession, user: User) -> str:
    """Yangi password reset token yaratadi va RAW qiymatni qaytaradi (emailga yuboriladi)."""
    raw = generate_url_token(32)
    record = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_token(raw),
        expires_at=_now() + PASSWORD_RESET_TTL,
    )
    db.add(record)
    await db.flush()
    return raw


async def consume_password_reset_token(db: AsyncSession, raw_token: str) -> User:
    """Token'ni topadi, yaroqliligini tekshiradi, ishlatilgan deb belgilaydi va User qaytaradi."""
    token_h = hash_token(raw_token)
    stmt = select(PasswordResetToken).where(PasswordResetToken.token_hash == token_h)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if record is None or record.used_at is not None or record.expires_at < _now():
        raise InvalidTokenError("Token yaroqsiz yoki muddati o'tgan")

    user = await db.get(User, record.user_id)
    if user is None or not user.is_active:
        raise InvalidTokenError("Foydalanuvchi mavjud emas yoki o'chirilgan")

    record.used_at = _now()
    await db.flush()
    return user


# ---------- Email verification ----------


async def issue_email_verification_token(db: AsyncSession, user: User) -> str:
    raw = generate_url_token(32)
    record = EmailVerificationToken(
        user_id=user.id,
        token=hash_token(raw),
        expires_at=_now() + EMAIL_VERIFICATION_TTL,
    )
    db.add(record)
    await db.flush()
    return raw


async def consume_email_verification_token(db: AsyncSession, raw_token: str) -> User:
    token_h = hash_token(raw_token)
    stmt = select(EmailVerificationToken).where(EmailVerificationToken.token == token_h)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if record is None or record.used_at is not None or record.expires_at < _now():
        raise InvalidTokenError("Token yaroqsiz yoki muddati o'tgan")

    user = await db.get(User, record.user_id)
    if user is None:
        raise InvalidTokenError("Foydalanuvchi topilmadi")

    user.is_verified = True
    record.used_at = _now()
    await db.flush()
    return user

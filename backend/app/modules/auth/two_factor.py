"""2FA TOTP servisi — Google Authenticator / Authy mos.

Spec: docs/03-modules/01-auth.md (3-bo'lim).
- TOTP secret User'ning `totp_secret` ustunida saqlanadi (production'da shifrlash tavsiya).
- 10 ta backup code yaratiladi, har biri SHA-256 hash sifatida `backup_codes` jadvalida (Phase 1d uchun
  alohida jadval qo'shamiz — login_attempts modelidan keyin qo'shildi).
- Joriy implementatsiyada backup codelarni `BackupCode` model bilan saqlaymiz.
"""

from __future__ import annotations

import secrets
from io import BytesIO

import pyotp
import qrcode
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_token, verify_password
from app.modules.auth.exceptions import InvalidCredentialsError, InvalidTotpError
from app.modules.auth.models import BackupCode  # type: ignore[attr-defined]
from app.modules.users.models import User

ISSUER = "XIU EduPlatform"


def generate_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(*, secret: str, account_name: str) -> str:
    """`otpauth://totp/...` URI — QR uchun."""
    return pyotp.TOTP(secret).provisioning_uri(name=account_name, issuer_name=ISSUER)


def make_qr_png(uri: str) -> bytes:
    qr = qrcode.QRCode(version=None, box_size=6, border=2)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def verify_totp(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=1)


# ---------- Backup codes ----------


def _generate_backup_code() -> str:
    """4-4 formatda (masalan 'a3f9-2k7p') — UI uchun qulay."""
    a = secrets.token_hex(2)
    b = secrets.token_hex(2)
    return f"{a}-{b}"


async def regenerate_backup_codes(db: AsyncSession, user: User, count: int = 10) -> list[str]:
    """Eski backup codelarni o'chiradi va yangi ro'yxat (raw) qaytaradi."""
    # Eski kodlarni o'chirish
    stmt = select(BackupCode).where(BackupCode.user_id == user.id)
    for bc in (await db.execute(stmt)).scalars().all():
        await db.delete(bc)

    raw_codes: list[str] = []
    for _ in range(count):
        code = _generate_backup_code()
        raw_codes.append(code)
        db.add(BackupCode(user_id=user.id, code_hash=hash_token(code)))
    await db.flush()
    return raw_codes


async def consume_backup_code(db: AsyncSession, user: User, code: str) -> bool:
    """Backup code'ni topsa, used_at belgilaydi va True qaytaradi."""
    stmt = select(BackupCode).where(
        BackupCode.user_id == user.id,
        BackupCode.code_hash == hash_token(code),
        BackupCode.used_at.is_(None),
    )
    result = await db.execute(stmt)
    bc = result.scalar_one_or_none()
    if bc is None:
        return False
    from datetime import UTC, datetime

    bc.used_at = datetime.now(UTC)
    await db.flush()
    return True


# ---------- Disable ----------


async def disable_2fa(db: AsyncSession, user: User, *, password: str) -> None:
    """Parol qayta-tasdiqlash bilan 2FA o'chirish."""
    if not user.password_hash or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()

    user.is_2fa_enabled = False
    user.totp_secret = None

    # Backup codelarni o'chirish
    stmt = select(BackupCode).where(BackupCode.user_id == user.id)
    for bc in (await db.execute(stmt)).scalars().all():
        await db.delete(bc)
    await db.flush()


async def verify_totp_or_backup(
    db: AsyncSession, user: User, code: str
) -> bool:
    """Login flow uchun: TOTP yoki backup code qabul qilamiz."""
    if not user.totp_secret:
        return False
    if verify_totp(user.totp_secret, code):
        return True
    return await consume_backup_code(db, user, code)


__all__ = [
    "ISSUER",
    "consume_backup_code",
    "disable_2fa",
    "generate_secret",
    "make_qr_png",
    "provisioning_uri",
    "regenerate_backup_codes",
    "verify_totp",
    "verify_totp_or_backup",
]

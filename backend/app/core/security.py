"""Xavfsizlik utilita'lari: parol hash, JWT, token rotation.

Spec: docs/03-modules/01-auth.md
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# bcrypt cost=12 (TZ talabi)
BCRYPT_ROUNDS = 12

# bcrypt 72-bayt cheklovi — uzun parollarni SHA-256 bilan oldindan hash qilamiz
_BCRYPT_MAX_BYTES = 72

TokenType = Literal["access", "refresh"]


# ---------- Parol ----------


def _prehash(password: str) -> bytes:
    """72 baytdan uzun parol uchun SHA-256 pre-hash (universal yondashuv)."""
    raw = password.encode("utf-8")
    if len(raw) <= _BCRYPT_MAX_BYTES:
        return raw
    return hashlib.sha256(raw).hexdigest().encode("utf-8")


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(_prehash(password), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(_prehash(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ---------- JWT ----------


def _now() -> datetime:
    return datetime.now(UTC)


def _create_token(
    subject: str | int,
    token_type: TokenType,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = _now()
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": secrets.token_urlsafe(16),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(
    subject: str | int,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    return _create_token(
        subject,
        "access",
        timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims,
    )


def create_refresh_token(subject: str | int) -> str:
    return _create_token(
        subject,
        "refresh",
        timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str, *, expected_type: TokenType | None = None) -> dict[str, Any]:
    """Token decode + validate. JWTError yoki tip mos kelmasa, ValueError."""
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError as exc:
        raise ValueError("invalid_token") from exc

    if expected_type and payload.get("type") != expected_type:
        raise ValueError("wrong_token_type")
    return payload


# ---------- Refresh token hash (DB'da saqlash uchun) ----------


def hash_token(token: str) -> str:
    """Refresh tokenni DB'da saqlash uchun SHA-256.

    Bcrypt kerak emas — token o'zi shovqin (high-entropy), faqat lookup uchun.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ---------- One-shot token (parol tiklash, email tasdiq) ----------


def generate_url_token(byte_length: int = 32) -> str:
    return secrets.token_urlsafe(byte_length)

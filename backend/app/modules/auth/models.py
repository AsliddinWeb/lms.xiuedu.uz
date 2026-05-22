"""Auth-bog'liq modellari: Session, LoginAttempt, PasswordResetToken, EmailVerificationToken, AuditLog.

Spec: docs/03-modules/01-auth.md, docs/07-devops/04-security.md
"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IDMixin, TimestampMixin


class UserSession(Base, IDMixin):
    """Foydalanuvchi sessiyasi — refresh token rotation, multi-device login."""

    __tablename__ = "user_sessions"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    refresh_token_hash: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    device_info: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class LoginAttempt(Base, IDMixin, TimestampMixin):
    """Login attempt audit log (brute-force tahlil + xavfsizlik tekshirish uchun)."""

    __tablename__ = "login_attempts"

    email: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    ip_address: Mapped[str] = mapped_column(INET, index=True, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)


class PasswordResetToken(Base, IDMixin, TimestampMixin):
    __tablename__ = "password_reset_tokens"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EmailVerificationToken(Base, IDMixin, TimestampMixin):
    __tablename__ = "email_verification_tokens"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BackupCode(Base, IDMixin, TimestampMixin):
    """2FA backup code — bir martalik."""

    __tablename__ = "backup_codes"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base, IDMixin, TimestampMixin):
    """Umumiy audit log — barcha sezgir amallarni qayd qiladi.

    Phase 11 da: oy bo'yicha partition (audit_logs_2026_05, va h.k.)
    """

    __tablename__ = "audit_logs"

    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

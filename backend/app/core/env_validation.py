"""Boot-time .env validation — Phase 7f.

Production'da xavfli default qiymatlarni rad etadi (dev secret bilan deploy
qilib qo'yilmasligi uchun). Application start vaqtida tekshiriladi.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


DEV_SECRETS = {
    "devkey",
    "devsecret_at_least_32_characters_long",
    "minio_dev_secret_at_least_32_chars",
    "ChangeMe!2026",
    "lms_dev_password",
    "secret-key-change-me",
    "change-me-in-prod",
}


class EnvValidationError(RuntimeError):
    """Production .env xavfli qiymatlar bilan ishga tushirilmoqda."""


def validate_production_env() -> None:
    """`APP_ENV=production` bo'lganda dev default'lar bo'lmasligini tekshirish.

    Xato chiqsa app ishga tushmaydi (fail-fast).
    """
    if not settings.is_production:
        return

    # Fatal issues — app boot to'xtatadi
    issues: list[str] = []
    # Warning'lar — log'ga yoziladi, lekin app ishga tushadi
    warnings: list[str] = []

    jwt_secret = getattr(settings, "JWT_SECRET_KEY", "")
    if jwt_secret in DEV_SECRETS or len(jwt_secret) < 32:
        issues.append("JWT_SECRET_KEY dev default yoki juda qisqa (<32 ch)")
    if settings.LIVEKIT_API_SECRET in DEV_SECRETS or len(settings.LIVEKIT_API_SECRET) < 32:
        issues.append("LIVEKIT_API_SECRET dev default yoki juda qisqa")
    if settings.MINIO_SECRET_KEY in DEV_SECRETS:
        issues.append("MINIO_SECRET_KEY dev default")
    db_url = str(settings.DATABASE_URL)
    if "lms_dev_password" in db_url or "@localhost" in db_url and settings.is_production:
        issues.append("DATABASE_URL dev parol / localhost ishlatmoqda")
    if settings.APP_DEBUG:
        issues.append("APP_DEBUG=True production'da yoqilgan")
    if not settings.cors_origins_list:
        issues.append("CORS_ORIGINS bo'sh — frontend ulanolmasligi mumkin")

    # SENTRY_DSN — ixtiyoriy, faqat warning
    if not settings.SENTRY_DSN:
        warnings.append("SENTRY_DSN bo'sh — xatolar Sentry'da kuzatilmaydi (ixtiyoriy)")

    for w in warnings:
        logger.warning("env.validation.warning", issue=w)

    if issues:
        for issue in issues:
            logger.error("env.validation.failed", issue=issue)
        raise EnvValidationError(
            "Production env tekshiruvi muvaffaqiyatsiz: "
            + "; ".join(issues)
            + ". Iltimos, .env ni to'g'irlang."
        )

    logger.info("env.validation.passed")

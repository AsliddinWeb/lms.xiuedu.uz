"""Phase 7f — env_validation unit testlari."""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.core.env_validation import EnvValidationError, validate_production_env


def test_non_production_passes_unconditionally(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "development", raising=False)
    # Should not raise even if dev secrets are present
    validate_production_env()


def test_production_with_dev_secrets_fails(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production", raising=False)
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "devkey", raising=False)
    monkeypatch.setattr(settings, "LIVEKIT_API_SECRET", "devsecret_at_least_32_characters_long", raising=False)
    monkeypatch.setattr(settings, "MINIO_SECRET_KEY", "minio_dev_secret_at_least_32_chars", raising=False)
    monkeypatch.setattr(settings, "SENTRY_DSN", "", raising=False)
    monkeypatch.setattr(settings, "APP_DEBUG", True, raising=False)
    with pytest.raises(EnvValidationError) as exc:
        validate_production_env()
    msg = str(exc.value)
    assert "JWT_SECRET_KEY" in msg
    assert "LIVEKIT_API_SECRET" in msg
    assert "MINIO_SECRET_KEY" in msg
    assert "SENTRY_DSN" in msg
    assert "APP_DEBUG" in msg


def test_production_with_good_values_passes(monkeypatch):
    from pydantic import PostgresDsn
    monkeypatch.setattr(settings, "APP_ENV", "production", raising=False)
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "a-very-long-random-secret-key-with-32-chars-or-more", raising=False)
    monkeypatch.setattr(settings, "LIVEKIT_API_SECRET", "another-very-long-random-livekit-api-secret-32+", raising=False)
    monkeypatch.setattr(settings, "MINIO_SECRET_KEY", "real-minio-secret-not-dev", raising=False)
    monkeypatch.setattr(settings, "SENTRY_DSN", "https://abc@sentry.io/123", raising=False)
    monkeypatch.setattr(settings, "APP_DEBUG", False, raising=False)
    monkeypatch.setattr(
        settings,
        "DATABASE_URL",
        PostgresDsn("postgresql+asyncpg://lms:strong-prod-pwd@prod-db:5432/lms"),
        raising=False,
    )
    monkeypatch.setattr(settings, "CORS_ORIGINS", "https://lms.xiuedu.uz", raising=False)
    validate_production_env()

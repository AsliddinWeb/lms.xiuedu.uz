"""Phase 1d testlari: forgot/reset password, email verification, 2FA TOTP."""

from __future__ import annotations

import uuid
from typing import Any

import pyotp
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete, select, text

from app.core.database import SessionLocal
from app.modules.auth.models import (
    BackupCode,
    EmailVerificationToken,
    LoginAttempt,
    PasswordResetToken,
    UserSession,
)
from app.modules.users.models import User

VALID_PASSWORD = "Str0ng!Password"


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def clean_for_1d():
    async with SessionLocal() as db:
        await db.execute(delete(UserSession))
        await db.execute(delete(LoginAttempt))
        await db.execute(delete(BackupCode))
        await db.execute(delete(EmailVerificationToken))
        await db.execute(delete(PasswordResetToken))
        await db.execute(
            text(
                "DELETE FROM user_roles WHERE user_id IN "
                "(SELECT id FROM users WHERE email LIKE '%@example.com')"
            )
        )
        await db.execute(
            text(
                "DELETE FROM profiles WHERE user_id IN "
                "(SELECT id FROM users WHERE email LIKE '%@example.com')"
            )
        )
        await db.execute(text("DELETE FROM users WHERE email LIKE '%@example.com'"))
        # admin'da 2FA qoldirgan bo'lsa tozalaymiz
        await db.execute(
            text("UPDATE users SET is_2fa_enabled=FALSE, totp_secret=NULL WHERE email='admin@xiuedu.uz'")
        )
        await db.commit()
    yield


def _email() -> str:
    return f"u_{uuid.uuid4().hex[:10]}@example.com"


async def _register_and_login(client: AsyncClient) -> tuple[str, str, str]:
    email = _email()
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD, "full_name": "Test User"},
    )
    r = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": VALID_PASSWORD}
    )
    return email, r.json()["access_token"], r.json()["refresh_token"]


async def _get_db_token(model: Any, email: str) -> str:
    """Test'lar uchun: yangi yaratilgan tokenni DB'dan olib emailda yuborilgan
    RAW token o'rniga ishlatish o'rniga, yangi token raw'ni service orqali olamiz."""
    async with SessionLocal() as db:
        user_stmt = select(User).where(User.email == email)
        user = (await db.execute(user_stmt)).scalar_one()

        if model is PasswordResetToken:
            from app.modules.auth.tokens import issue_password_reset_token

            raw = await issue_password_reset_token(db, user)
        else:
            from app.modules.auth.tokens import issue_email_verification_token

            raw = await issue_email_verification_token(db, user)
        await db.commit()
        return raw


# ---------- Email verification ----------


async def test_register_creates_verification_token(client: AsyncClient) -> None:
    email = _email()
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD, "full_name": "Test"},
    )
    assert r.status_code == 201
    async with SessionLocal() as db:
        user = (
            await db.execute(select(User).where(User.email == email))
        ).scalar_one()
        tokens = (
            await db.execute(
                select(EmailVerificationToken).where(EmailVerificationToken.user_id == user.id)
            )
        ).scalars().all()
        assert len(tokens) == 1
        assert user.is_verified is False


async def test_verify_email_with_valid_token(client: AsyncClient) -> None:
    email = _email()
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD, "full_name": "Test"},
    )
    raw = await _get_db_token(EmailVerificationToken, email)
    r = await client.post("/api/v1/auth/verify-email", json={"token": raw})
    assert r.status_code == 204

    async with SessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one()
        assert user.is_verified is True


async def test_verify_email_invalid_token(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/auth/verify-email", json={"token": "x" * 32}
    )
    assert r.status_code == 401


async def test_verify_email_token_single_use(client: AsyncClient) -> None:
    email = _email()
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD, "full_name": "Test"},
    )
    raw = await _get_db_token(EmailVerificationToken, email)
    assert (await client.post("/api/v1/auth/verify-email", json={"token": raw})).status_code == 204
    # Ikkinchi marta — yaroqsiz
    r = await client.post("/api/v1/auth/verify-email", json={"token": raw})
    assert r.status_code == 401


# ---------- Forgot / Reset password ----------


async def test_forgot_password_returns_204_for_unknown_email(client: AsyncClient) -> None:
    """User-enumeration himoyasi: noma'lum email uchun ham 204."""
    r = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "ghost@example.com"}
    )
    assert r.status_code == 204


async def test_forgot_password_creates_token_for_known_email(client: AsyncClient) -> None:
    email, _, _ = await _register_and_login(client)
    # Verify the user first so tokens are clean
    raw = await _get_db_token(EmailVerificationToken, email)
    await client.post("/api/v1/auth/verify-email", json={"token": raw})

    r = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert r.status_code == 204

    async with SessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one()
        tokens = (
            await db.execute(
                select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
            )
        ).scalars().all()
        assert len(tokens) >= 1


async def test_reset_password_changes_password(client: AsyncClient) -> None:
    email, _, _ = await _register_and_login(client)
    raw = await _get_db_token(PasswordResetToken, email)

    new_pass = "BrandNew!2026"
    r = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw, "new_password": new_pass},
    )
    assert r.status_code == 204

    # Yangi parol ishlaydi
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": new_pass}
    )
    assert login.status_code == 200

    # Eski parol ishlamaydi
    old = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": VALID_PASSWORD}
    )
    assert old.status_code == 401


async def test_reset_password_token_single_use(client: AsyncClient) -> None:
    email, _, _ = await _register_and_login(client)
    raw = await _get_db_token(PasswordResetToken, email)

    new_pass = "BrandNew!2026"
    assert (
        await client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw, "new_password": new_pass},
        )
    ).status_code == 204

    # Bir xil token bilan qayta urinish
    r = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw, "new_password": new_pass},
    )
    assert r.status_code == 401


async def test_change_password_requires_old(client: AsyncClient) -> None:
    _email_, access, _ = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {access}"}

    r = await client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "wrong", "new_password": "Aaaaaa!1234"},
        headers=headers,
    )
    assert r.status_code == 401

    r = await client.post(
        "/api/v1/auth/change-password",
        json={"old_password": VALID_PASSWORD, "new_password": "Newer!Pass2026"},
        headers=headers,
    )
    assert r.status_code == 204


# ---------- 2FA ----------


async def _admin_token(client: AsyncClient) -> str:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@xiuedu.uz", "password": "ChangeMe!2026"},
    )
    return r.json()["access_token"]


async def test_2fa_setup_returns_secret_and_qr(client: AsyncClient) -> None:
    token = await _admin_token(client)
    r = await client.post(
        "/api/v1/auth/2fa/setup", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["secret"]
    assert body["otpauth_uri"].startswith("otpauth://totp/")
    assert len(body["qr_png_base64"]) > 100


async def test_2fa_enable_with_valid_code(client: AsyncClient) -> None:
    token = await _admin_token(client)
    setup = await client.post(
        "/api/v1/auth/2fa/setup", headers={"Authorization": f"Bearer {token}"}
    )
    secret = setup.json()["secret"]
    code = pyotp.TOTP(secret).now()

    r = await client.post(
        "/api/v1/auth/2fa/enable",
        json={"code": code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert len(r.json()["backup_codes"]) == 10


async def test_2fa_login_requires_totp(client: AsyncClient) -> None:
    token = await _admin_token(client)
    setup = await client.post(
        "/api/v1/auth/2fa/setup", headers={"Authorization": f"Bearer {token}"}
    )
    secret = setup.json()["secret"]
    await client.post(
        "/api/v1/auth/2fa/enable",
        json={"code": pyotp.TOTP(secret).now()},
        headers={"Authorization": f"Bearer {token}"},
    )

    # 2FA yoqilgan akkaunt — parol bilan login 2FA kod talab qiladi
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@xiuedu.uz", "password": "ChangeMe!2026"},
    )
    assert r.status_code == 401
    assert "2FA" in r.json()["detail"]


async def test_2fa_login_with_totp_succeeds(client: AsyncClient) -> None:
    token = await _admin_token(client)
    setup = await client.post(
        "/api/v1/auth/2fa/setup", headers={"Authorization": f"Bearer {token}"}
    )
    secret = setup.json()["secret"]
    await client.post(
        "/api/v1/auth/2fa/enable",
        json={"code": pyotp.TOTP(secret).now()},
        headers={"Authorization": f"Bearer {token}"},
    )

    r = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@xiuedu.uz",
            "password": "ChangeMe!2026",
            "totp_code": pyotp.TOTP(secret).now(),
        },
    )
    assert r.status_code == 200
    assert "access_token" in r.json()


async def test_2fa_backup_code_works_once(client: AsyncClient) -> None:
    token = await _admin_token(client)
    setup = await client.post(
        "/api/v1/auth/2fa/setup", headers={"Authorization": f"Bearer {token}"}
    )
    secret = setup.json()["secret"]
    enable = await client.post(
        "/api/v1/auth/2fa/enable",
        json={"code": pyotp.TOTP(secret).now()},
        headers={"Authorization": f"Bearer {token}"},
    )
    backup = enable.json()["backup_codes"][0]

    # Birinchi marta ishlaydi
    r1 = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@xiuedu.uz",
            "password": "ChangeMe!2026",
            "totp_code": backup,
        },
    )
    assert r1.status_code == 200

    # Ikkinchi marta — endi yaroqsiz
    r2 = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@xiuedu.uz",
            "password": "ChangeMe!2026",
            "totp_code": backup,
        },
    )
    assert r2.status_code == 401


async def test_2fa_disable_with_password_and_code(client: AsyncClient) -> None:
    token = await _admin_token(client)
    setup = await client.post(
        "/api/v1/auth/2fa/setup", headers={"Authorization": f"Bearer {token}"}
    )
    secret = setup.json()["secret"]
    await client.post(
        "/api/v1/auth/2fa/enable",
        json={"code": pyotp.TOTP(secret).now()},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Re-login (2FA bilan) — yangi token kerak
    relogin = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@xiuedu.uz",
            "password": "ChangeMe!2026",
            "totp_code": pyotp.TOTP(secret).now(),
        },
    )
    new_token = relogin.json()["access_token"]

    r = await client.post(
        "/api/v1/auth/2fa/disable",
        json={"password": "ChangeMe!2026", "code": pyotp.TOTP(secret).now()},
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert r.status_code == 204

    # Endi parol+kodsiz ham login
    r2 = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@xiuedu.uz", "password": "ChangeMe!2026"},
    )
    assert r2.status_code == 200

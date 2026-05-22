"""Auth integration testlari — register/login/refresh/me/brute-force.

Testlar real DB va Redis bilan ishlaydi (docker compose ko'tarilgan bo'lishi kerak).
Har test boshida tegishli jadvallar tozalanadi.
"""

from __future__ import annotations

import uuid

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete, text

from app.core.database import SessionLocal
from app.core.redis import redis_client
from app.modules.auth.models import LoginAttempt, UserSession


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def clean_db_redis():
    """Har test oldidan auth jadvallarini va Redis'ni tozalash."""
    async with SessionLocal() as db:
        # Tartib: FK ni hisobga olib
        await db.execute(delete(UserSession))
        await db.execute(delete(LoginAttempt))
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
        await db.commit()

    keys = []
    async for k in redis_client.scan_iter(match="auth:*"):
        keys.append(k)
    if keys:
        await redis_client.delete(*keys)

    yield


def _email() -> str:
    return f"u_{uuid.uuid4().hex[:10]}@example.com"


VALID_PASSWORD = "Str0ng!Password"


async def test_register_success(client: AsyncClient) -> None:
    email = _email()
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD, "full_name": "Test Talaba"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == email
    assert body["is_active"] is True
    assert body["is_verified"] is False
    assert body["roles"] == []


async def test_register_duplicate(client: AsyncClient) -> None:
    email = _email()
    payload = {"email": email, "password": VALID_PASSWORD, "full_name": "Test"}
    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 201
    r = await client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 409
    assert r.json()["detail"].startswith("Bu email")


async def test_register_weak_password(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": _email(), "password": "weakweakweak", "full_name": "Test"},
    )
    assert r.status_code == 422


async def test_login_success_returns_tokens(client: AsyncClient) -> None:
    email = _email()
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD, "full_name": "Test"},
    )
    r = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": VALID_PASSWORD}
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["expires_in"] == 15 * 60


async def test_login_invalid_password(client: AsyncClient) -> None:
    email = _email()
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD, "full_name": "Test"},
    )
    r = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "Wrong!Password1"}
    )
    assert r.status_code == 401
    assert r.json()["detail"].startswith("Email yoki parol")


async def test_brute_force_lock_after_5_attempts(client: AsyncClient) -> None:
    email = _email()
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD, "full_name": "Test"},
    )
    for _ in range(5):
        r = await client.post(
            "/api/v1/auth/login", json={"email": email, "password": "Wrong!Password1"}
        )
        assert r.status_code == 401

    # 6-urinish: blokda
    r = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": VALID_PASSWORD}
    )
    assert r.status_code == 423
    assert "bloklangan" in r.json()["detail"]


async def test_me_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


async def test_me_with_token_returns_user(client: AsyncClient) -> None:
    email = _email()
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD, "full_name": "Test"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": VALID_PASSWORD}
    )
    token = login.json()["access_token"]

    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert r.json()["email"] == email


async def test_refresh_rotates_token(client: AsyncClient) -> None:
    email = _email()
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD, "full_name": "Test"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": VALID_PASSWORD}
    )
    refresh = login.json()["refresh_token"]

    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200, r.text
    new_refresh = r.json()["refresh_token"]
    assert new_refresh != refresh

    # Eski refresh — endi revoked
    r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r2.status_code == 401


async def test_logout_revokes_refresh(client: AsyncClient) -> None:
    email = _email()
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD, "full_name": "Test"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": VALID_PASSWORD}
    )
    refresh = login.json()["refresh_token"]

    logout = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh})
    assert logout.status_code == 204

    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 401

"""HEMIS SSO testlari — httpx.AsyncClient ni mock qilamiz.

HEMIS API real chaqirilmaydi — `httpx.AsyncClient` ni MockTransport bilan o'rab,
oldindan tayyorlangan javoblarni qaytaramiz.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete, select, text

from app.core.database import SessionLocal
from app.modules.auth.models import LoginAttempt, UserSession
from app.modules.users.models import User


# ---------- Stub HEMIS server ----------


class HemisStub:
    """HEMIS server simulyatsiyasi — testlarda monkey-patch qilinadi."""

    def __init__(self) -> None:
        self.expected_login = "999211100073"
        self.expected_password = "DD7777777"
        self.student: dict[str, Any] = {
            "id": 1234567,
            "first_name": "Ali",
            "second_name": "Valiyev",
            "third_name": "Bahodir o'g'li",
            "full_name": "Valiyev Ali Bahodir o'g'li",
            "student_id_number": "999211100073",
            "passport_pin": "30101019999999",
            "email": "ali.valiyev@stud.xiuedu.uz",
            "image": "https://student.xiuedu.uz/files/avatar/123.jpg",
        }

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/v1/auth/login"):
            import json as _json

            data = _json.loads(request.content or b"{}")
            if (
                data.get("login") == self.expected_login
                and data.get("password") == self.expected_password
            ):
                return httpx.Response(
                    200,
                    json={
                        "success": True,
                        "error": None,
                        "code": 200,
                        "data": {"token": "stub-jwt-token"},
                    },
                    headers={"Set-Cookie": "refresh-token=stub-refresh-cookie; path=/"},
                )
            return httpx.Response(
                200,
                json={"success": False, "error": "Invalid credentials", "code": 401, "data": None},
            )
        if path.endswith("/v1/account/me"):
            auth = request.headers.get("authorization", "")
            if auth != "Bearer stub-jwt-token":
                return httpx.Response(401, json={"success": False, "error": "unauth"})
            return httpx.Response(
                200,
                json={"success": True, "error": None, "code": 200, "data": self.student},
            )
        return httpx.Response(404, json={"success": False, "error": "not found"})


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def clean_hemis_users(monkeypatch):
    """Test boshida HEMIS akkauntlarni tozalash + httpx mock o'rnatish."""
    async with SessionLocal() as db:
        await db.execute(delete(UserSession))
        await db.execute(delete(LoginAttempt))
        await db.execute(
            text(
                "DELETE FROM user_roles WHERE user_id IN "
                "(SELECT id FROM users WHERE hemis_id IS NOT NULL OR email LIKE '%@example.com' "
                "OR email LIKE '%@local.xiuedu.uz' OR email LIKE '%@stud.xiuedu.uz')"
            )
        )
        await db.execute(
            text(
                "DELETE FROM profiles WHERE user_id IN "
                "(SELECT id FROM users WHERE hemis_id IS NOT NULL OR email LIKE '%@example.com' "
                "OR email LIKE '%@local.xiuedu.uz' OR email LIKE '%@stud.xiuedu.uz')"
            )
        )
        await db.execute(
            text(
                "DELETE FROM users WHERE hemis_id IS NOT NULL OR email LIKE '%@example.com' "
                "OR email LIKE '%@local.xiuedu.uz' OR email LIKE '%@stud.xiuedu.uz'"
            )
        )
        await db.commit()

    # HEMIS HTTP'ni mock qilamiz
    stub = HemisStub()
    transport = httpx.MockTransport(stub)
    real_init = httpx.AsyncClient.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = transport
        return real_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)
    yield stub


# ---------- Tests ----------


async def test_hemis_login_creates_new_user(
    client: AsyncClient, clean_hemis_users: HemisStub
) -> None:
    r = await client.post(
        "/api/v1/auth/login/hemis",
        json={"login": clean_hemis_users.expected_login, "password": clean_hemis_users.expected_password},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["access_token"]
    assert body["refresh_token"]

    # User DB'da yaratilganmi?
    async with SessionLocal() as db:
        u = (
            await db.execute(
                select(User).where(User.hemis_id == clean_hemis_users.student["id"])
            )
        ).scalar_one()
        assert u.full_name == "Valiyev Ali Bahodir o'g'li"
        assert u.is_verified is True
        assert u.password_hash is None  # HEMIS-only akkaunt
        assert u.email == "ali.valiyev@stud.xiuedu.uz"


async def test_hemis_login_attaches_student_role(
    client: AsyncClient, clean_hemis_users: HemisStub
) -> None:
    r = await client.post(
        "/api/v1/auth/login/hemis",
        json={"login": clean_hemis_users.expected_login, "password": clean_hemis_users.expected_password},
    )
    token = r.json()["access_token"]

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert "student" in me.json()["roles"]


async def test_hemis_login_idempotent(
    client: AsyncClient, clean_hemis_users: HemisStub
) -> None:
    """Ikkinchi login mavjud userga bog'lanadi, dublikat yaratmaydi."""
    payload = {
        "login": clean_hemis_users.expected_login,
        "password": clean_hemis_users.expected_password,
    }
    r1 = await client.post("/api/v1/auth/login/hemis", json=payload)
    r2 = await client.post("/api/v1/auth/login/hemis", json=payload)
    assert r1.status_code == 200
    assert r2.status_code == 200

    async with SessionLocal() as db:
        count = (
            await db.execute(
                select(User).where(User.hemis_id == clean_hemis_users.student["id"])
            )
        ).scalars().all()
        assert len(count) == 1


async def test_hemis_login_invalid_credentials(
    client: AsyncClient, clean_hemis_users: HemisStub
) -> None:
    r = await client.post(
        "/api/v1/auth/login/hemis",
        json={"login": "wrong", "password": "wrong"},
    )
    assert r.status_code == 401
    assert "HEMIS" in r.json()["detail"]


async def test_hemis_links_existing_user_by_email(
    client: AsyncClient, clean_hemis_users: HemisStub
) -> None:
    """Agar HEMIS bergan email bilan user mavjud bo'lsa — uni linklaymiz."""
    # Avval oddiy register orqali yaratamiz
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": clean_hemis_users.student["email"],
            "password": "Str0ng!Password",
            "full_name": "Old Name",
        },
    )
    # Endi HEMIS orqali login
    r = await client.post(
        "/api/v1/auth/login/hemis",
        json={
            "login": clean_hemis_users.expected_login,
            "password": clean_hemis_users.expected_password,
        },
    )
    assert r.status_code == 200

    async with SessionLocal() as db:
        u = (
            await db.execute(
                select(User).where(User.email == clean_hemis_users.student["email"])
            )
        ).scalar_one()
        assert u.hemis_id == clean_hemis_users.student["id"]
        # Full name yangilanadi (HEMIS authoritative)
        assert u.full_name == "Valiyev Ali Bahodir o'g'li"
        assert u.is_verified is True

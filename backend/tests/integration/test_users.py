"""Users CRUD integration testlari + RBAC enforcement."""

from __future__ import annotations

import uuid

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete, text

from app.core.database import SessionLocal
from app.modules.auth.models import LoginAttempt, UserSession

VALID_PASSWORD = "Str0ng!Password"
ADMIN_EMAIL = "admin@xiuedu.uz"
ADMIN_PASSWORD = "ChangeMe!2026"


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def clean_users():
    async with SessionLocal() as db:
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
    yield


def _email() -> str:
    return f"u_{uuid.uuid4().hex[:10]}@example.com"


async def _admin_token(client: AsyncClient) -> str:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    return r.json()["access_token"]


async def _student_token(client: AsyncClient) -> tuple[str, str]:
    email = _email()
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD, "full_name": "Student Test"},
    )
    r = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": VALID_PASSWORD}
    )
    return r.json()["access_token"], email


# ---------- RBAC enforcement ----------


async def test_users_list_forbidden_without_auth(client: AsyncClient) -> None:
    r = await client.get("/api/v1/users")
    assert r.status_code == 401


async def test_users_list_forbidden_for_student(client: AsyncClient) -> None:
    token, _ = await _student_token(client)
    r = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


async def test_users_list_allowed_for_admin(client: AsyncClient) -> None:
    token = await _admin_token(client)
    r = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "total" in body


# ---------- Default role on register ----------


async def test_register_attaches_student_role(client: AsyncClient) -> None:
    token, _ = await _student_token(client)
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    body = me.json()
    assert "student" in body["roles"]
    assert "course.read" in body["permissions"]


# ---------- CRUD ----------


async def test_admin_can_create_user_with_roles(client: AsyncClient) -> None:
    admin_token = await _admin_token(client)
    payload = {
        "email": _email(),
        "password": VALID_PASSWORD,
        "full_name": "Test Pedagog",
        "role_codes": ["teacher"],
    }
    r = await client.post(
        "/api/v1/users",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == payload["email"]
    assert "teacher" in body["roles"]


async def test_admin_can_filter_users_by_role(client: AsyncClient) -> None:
    admin_token = await _admin_token(client)
    await _student_token(client)  # bitta talaba yaratamiz

    r = await client.get(
        "/api/v1/users?role=student",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert all("student" in u["roles"] for u in body["items"])
    assert body["total"] >= 1


async def test_admin_can_search_users(client: AsyncClient) -> None:
    admin_token = await _admin_token(client)
    _, email = await _student_token(client)

    r = await client.get(
        f"/api/v1/users?q={email[:8]}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.json()["total"] >= 1


async def test_admin_can_deactivate_user(client: AsyncClient) -> None:
    admin_token = await _admin_token(client)
    create = await client.post(
        "/api/v1/users",
        json={
            "email": _email(),
            "password": VALID_PASSWORD,
            "full_name": "Test",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    user_id = create.json()["id"]

    r = await client.post(
        f"/api/v1/users/{user_id}/deactivate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.json()["is_active"] is False


async def test_admin_cannot_deactivate_self(client: AsyncClient) -> None:
    admin_token = await _admin_token(client)
    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_token}"}
    )
    admin_id = me.json()["id"]

    r = await client.post(
        f"/api/v1/users/{admin_id}/deactivate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 409


async def test_admin_can_update_user(client: AsyncClient) -> None:
    admin_token = await _admin_token(client)
    create = await client.post(
        "/api/v1/users",
        json={"email": _email(), "password": VALID_PASSWORD, "full_name": "Old Name"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    user_id = create.json()["id"]

    r = await client.patch(
        f"/api/v1/users/{user_id}",
        json={"full_name": "New Name", "is_verified": True},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["full_name"] == "New Name"
    assert body["is_verified"] is True


async def test_admin_can_replace_roles(client: AsyncClient) -> None:
    admin_token = await _admin_token(client)
    create = await client.post(
        "/api/v1/users",
        json={
            "email": _email(),
            "password": VALID_PASSWORD,
            "full_name": "Multi Role",
            "role_codes": ["student"],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    user_id = create.json()["id"]

    r = await client.put(
        f"/api/v1/users/{user_id}/roles",
        json=["teacher", "department_head"],
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 204

    detail = await client.get(
        f"/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    roles = detail.json()["roles"]
    assert "teacher" in roles
    assert "department_head" in roles
    assert "student" not in roles


# ---------- Roles + Permissions ----------


async def test_roles_endpoint_returns_10_roles(client: AsyncClient) -> None:
    admin_token = await _admin_token(client)
    r = await client.get("/api/v1/roles", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    roles = r.json()
    codes = {role["code"] for role in roles}
    assert {"super_admin", "otm_admin", "teacher", "student"} <= codes


async def test_permissions_endpoint(client: AsyncClient) -> None:
    admin_token = await _admin_token(client)
    r = await client.get(
        "/api/v1/permissions", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert r.status_code == 200
    perms = r.json()
    codes = {p["code"] for p in perms}
    assert "platform.*" in codes
    assert "users.manage" in codes

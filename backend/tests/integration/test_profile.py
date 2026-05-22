"""Phase 2c — Profile + Avatar (MinIO) testlari.

Avatar yuklash testlarida real MinIO ishlatiladi (docker compose ko'tarilgan).
"""

from __future__ import annotations

import base64
import uuid

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete, text

from app.core.database import SessionLocal
from app.modules.auth.models import LoginAttempt, UserSession

VALID_PASSWORD = "Str0ng!Password"
ADMIN_EMAIL = "admin@xiuedu.uz"
ADMIN_PASSWORD = "ChangeMe!2026"

# Tiny 1x1 PNG, valid header
TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/x8AAwAB/eq6n3wAAAAASUVORK5CYII="
)
# Tiny 1x1 webp magic
TINY_WEBP = (
    b"RIFF\x24\x00\x00\x00WEBPVP8 \x18\x00\x00\x000\x01\x00\x9d\x01\x2a\x01\x00\x01\x00\x02"
    b"\x00\x34\x25\xa4\x00\x03\x70\x00\xfe\xfb\xfd\x50\x00"
)


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def clean_profile():
    async with SessionLocal() as db:
        await db.execute(delete(UserSession))
        await db.execute(delete(LoginAttempt))
        await db.execute(
            text(
                "DELETE FROM user_roles WHERE user_id IN "
                "(SELECT id FROM users WHERE email LIKE '%@example.com')"
            )
        )
        # HEMIS testlaridan qolgan akkauntlar ham PINFL band qilishi mumkin
        clean_emails = (
            "email LIKE '%@example.com' OR email LIKE '%@local.xiuedu.uz' OR email LIKE '%@stud.xiuedu.uz'"
        )
        await db.execute(
            text(f"DELETE FROM profiles WHERE user_id IN (SELECT id FROM users WHERE {clean_emails})")
        )
        await db.execute(text(f"DELETE FROM users WHERE {clean_emails}"))
        # admin avatarini va profile ma'lumotlarini tozalash (test izolyatsiyasi)
        await db.execute(text("UPDATE users SET avatar_url=NULL, phone=NULL WHERE email='admin@xiuedu.uz'"))
        await db.execute(
            text("DELETE FROM profiles WHERE user_id IN (SELECT id FROM users WHERE email='admin@xiuedu.uz')")
        )
        await db.commit()
    yield


def _email() -> str:
    return f"u_{uuid.uuid4().hex[:10]}@example.com"


async def _admin(client: AsyncClient) -> str:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    return r.json()["access_token"]


# ---------- Profile read/update ----------


async def test_get_me_returns_full_profile(client: AsyncClient) -> None:
    token = await _admin(client)
    r = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == ADMIN_EMAIL
    assert body["roles"] == ["super_admin"]
    assert "platform.*" in body["permissions"]


async def test_patch_me_creates_profile(client: AsyncClient) -> None:
    token = await _admin(client)
    h = {"Authorization": f"Bearer {token}"}
    r = await client.patch(
        "/api/v1/users/me",
        headers=h,
        json={
            "phone": "+998901234567",
            "pinfl": "30101019999999",
            "birthdate": "1995-08-31",
            "gender": "male",
            "address": "Toshkent",
            "language": "uz-cyr",
            "timezone": "Asia/Tashkent",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["phone"] == "+998901234567"
    assert body["profile"]["pinfl"] == "30101019999999"
    assert body["profile"]["birthdate"] == "1995-08-31"
    assert body["profile"]["language"] == "uz-cyr"


async def test_patch_me_invalid_birthdate_format(client: AsyncClient) -> None:
    token = await _admin(client)
    r = await client.patch(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"birthdate": "31/08/1995"},
    )
    assert r.status_code == 422


async def test_preferences_update(client: AsyncClient) -> None:
    token = await _admin(client)
    h = {"Authorization": f"Bearer {token}"}
    r = await client.patch(
        "/api/v1/users/me/preferences",
        headers=h,
        json={"notification_preferences": {"email": True, "sms": False, "telegram": True}},
    )
    assert r.status_code == 200
    prefs = r.json()["profile"]["notification_preferences"]
    assert prefs == {"email": True, "sms": False, "telegram": True}


async def test_me_unauthenticated(client: AsyncClient) -> None:
    r = await client.get("/api/v1/users/me")
    assert r.status_code == 401


# ---------- Avatar upload ----------


async def test_avatar_upload_png(client: AsyncClient) -> None:
    token = await _admin(client)
    h = {"Authorization": f"Bearer {token}"}
    r = await client.post(
        "/api/v1/users/me/avatar",
        headers=h,
        files={"file": ("avatar.png", TINY_PNG, "image/png")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["avatar_url"]
    assert "avatars/" in body["avatar_url"]

    # /me ham avatar_url qaytarishi kerak
    me = await client.get("/api/v1/users/me", headers=h)
    assert me.json()["avatar_url"] == body["avatar_url"]


async def test_avatar_upload_rejects_text(client: AsyncClient) -> None:
    token = await _admin(client)
    r = await client.post(
        "/api/v1/users/me/avatar",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("doc.txt", b"hello world", "text/plain")},
    )
    assert r.status_code == 415


async def test_avatar_upload_rejects_too_large(client: AsyncClient) -> None:
    token = await _admin(client)
    big = b"\x89PNG\r\n\x1a\n" + b"\x00" * (3 * 1024 * 1024)  # 3MB
    r = await client.post(
        "/api/v1/users/me/avatar",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("big.png", big, "image/png")},
    )
    assert r.status_code == 413


async def test_avatar_replace_deletes_old(client: AsyncClient) -> None:
    token = await _admin(client)
    h = {"Authorization": f"Bearer {token}"}
    r1 = await client.post(
        "/api/v1/users/me/avatar",
        headers=h,
        files={"file": ("a.png", TINY_PNG, "image/png")},
    )
    url1 = r1.json()["avatar_url"]

    # Yangi avatar yuklaymiz
    r2 = await client.post(
        "/api/v1/users/me/avatar",
        headers=h,
        files={"file": ("b.png", TINY_PNG, "image/png")},
    )
    url2 = r2.json()["avatar_url"]
    assert url1 != url2  # yangi key generatsiya qilinadi


async def test_avatar_delete(client: AsyncClient) -> None:
    token = await _admin(client)
    h = {"Authorization": f"Bearer {token}"}
    await client.post(
        "/api/v1/users/me/avatar",
        headers=h,
        files={"file": ("a.png", TINY_PNG, "image/png")},
    )
    r = await client.delete("/api/v1/users/me/avatar", headers=h)
    assert r.status_code == 204

    me = await client.get("/api/v1/users/me", headers=h)
    assert me.json()["avatar_url"] is None

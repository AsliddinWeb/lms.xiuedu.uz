"""Phase 3a — Content backend smoke tests.

Coverage:
  - RBAC: talaba content.create yo'q (403); o'qituvchi yarata oladi
  - CRUD: yaratish, ro'yxat, get, update, soft-delete
  - Status workflow: draft → published; published'ni tahrirlab bo'lmaydi
  - Validation: link uchun file_url majburiy; text uchun content_data majburiy
  - Filter: type/status/q parametrlari ishlaydi
"""

from __future__ import annotations

import uuid

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete, text

from app.core.database import SessionLocal
from app.modules.academic.models import (
    AcademicCalendar,
    Curriculum,
    CurriculumSubject,
    Department,
    Faculty,
    Specialty,
    Subject,
    SubjectPrerequisite,
)
from app.modules.auth.models import LoginAttempt, UserSession
from app.modules.content.models import ContentItem
from app.modules.organizations.models import Organization

VALID_PASSWORD = "Str0ng!Password"
ADMIN_EMAIL = "admin@xiuedu.uz"
ADMIN_PASSWORD = "ChangeMe!2026"
TEACHER_EMAIL = "teacher@xiuedu.uz"
TEACHER_PASSWORD = "Teacher!2026"


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def clean_content():
    async with SessionLocal() as db:
        await db.execute(delete(ContentItem))
        await db.execute(delete(CurriculumSubject))
        await db.execute(delete(Curriculum))
        await db.execute(delete(SubjectPrerequisite))
        await db.execute(delete(Subject))
        await db.execute(delete(Specialty))
        await db.execute(delete(Department))
        await db.execute(delete(Faculty))
        await db.execute(delete(AcademicCalendar))
        await db.execute(delete(Organization))
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


async def _login(client: AsyncClient, email: str, password: str) -> str:
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


async def _admin(client: AsyncClient) -> str:
    return await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)


async def _teacher(client: AsyncClient) -> str:
    return await _login(client, TEACHER_EMAIL, TEACHER_PASSWORD)


async def _student(client: AsyncClient) -> str:
    email = _email()
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD, "full_name": "Talaba"},
    )
    return await _login(client, email, VALID_PASSWORD)


# ----------------------------------------------------------------------------
# RBAC
# ----------------------------------------------------------------------------


async def test_student_cannot_create_content(client: AsyncClient) -> None:
    token = await _student(client)
    r = await client.post(
        "/api/v1/content",
        json={"type": "text", "title": "Test", "content_data": {"ops": []}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


async def test_student_can_read_content(client: AsyncClient) -> None:
    token = await _student(client)
    r = await client.get(
        "/api/v1/content", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    assert "items" in r.json()


async def test_teacher_can_create_text_content(client: AsyncClient) -> None:
    token = await _teacher(client)
    r = await client.post(
        "/api/v1/content",
        json={
            "type": "text",
            "title": "Algoritmlar haqida kirish",
            "description": "Birinchi ma'ruza matni",
            "content_data": {"ops": [{"insert": "Salom dunyo\n"}]},
            "language": "uz-lat",
            "tags": ["algorithms", "intro"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "draft"
    assert body["version"] == 1
    assert body["type"] == "text"
    assert body["author_id"] > 0


# ----------------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------------


async def test_link_requires_file_url(client: AsyncClient) -> None:
    token = await _teacher(client)
    r = await client.post(
        "/api/v1/content",
        json={"type": "link", "title": "Tashqi havola"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422
    assert any("file_url" in str(d).lower() for d in r.json()["detail"])


async def test_text_requires_content_data(client: AsyncClient) -> None:
    token = await _teacher(client)
    r = await client.post(
        "/api/v1/content",
        json={"type": "text", "title": "Bo'sh matn"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422
    assert any("content_data" in str(d).lower() for d in r.json()["detail"])


# ----------------------------------------------------------------------------
# CRUD
# ----------------------------------------------------------------------------


async def _create_text(client: AsyncClient, token: str, title: str = "T") -> dict:
    r = await client.post(
        "/api/v1/content",
        json={
            "type": "text",
            "title": title,
            "content_data": {"ops": [{"insert": title}]},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    return r.json()


async def test_get_and_update_content(client: AsyncClient) -> None:
    token = await _teacher(client)
    item = await _create_text(client, token, "Eski sarlavha")

    g = await client.get(
        f"/api/v1/content/{item['id']}", headers={"Authorization": f"Bearer {token}"}
    )
    assert g.status_code == 200
    assert g.json()["id"] == item["id"]

    u = await client.patch(
        f"/api/v1/content/{item['id']}",
        json={"title": "Yangi sarlavha", "tags": ["updated"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert u.status_code == 200
    assert u.json()["title"] == "Yangi sarlavha"
    assert u.json()["tags"] == ["updated"]


async def test_soft_delete_hides_from_list(client: AsyncClient) -> None:
    token = await _teacher(client)
    item = await _create_text(client, token, "O'chiriladigan")

    d = await client.delete(
        f"/api/v1/content/{item['id']}", headers={"Authorization": f"Bearer {token}"}
    )
    assert d.status_code == 204

    g = await client.get(
        f"/api/v1/content/{item['id']}", headers={"Authorization": f"Bearer {token}"}
    )
    assert g.status_code == 404


# ----------------------------------------------------------------------------
# Status workflow
# ----------------------------------------------------------------------------


async def test_publish_transition(client: AsyncClient) -> None:
    token = await _teacher(client)
    item = await _create_text(client, token, "Publish qilinadigan")

    r = await client.post(
        f"/api/v1/content/{item['id']}/publish",
        json={"status": "published"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "published"
    assert body["published_at"] is not None


async def test_published_cannot_be_edited(client: AsyncClient) -> None:
    token = await _teacher(client)
    item = await _create_text(client, token, "Locked")

    pub = await client.post(
        f"/api/v1/content/{item['id']}/publish",
        json={"status": "published"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert pub.status_code == 200

    u = await client.patch(
        f"/api/v1/content/{item['id']}",
        json={"title": "Yangilashga urinish"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert u.status_code == 409


async def test_invalid_transition_rejected(client: AsyncClient) -> None:
    token = await _teacher(client)
    item = await _create_text(client, token, "Direct archive")

    # archive → draft ruxsat etilgan, ammo published'siz draft → archived ham mumkin.
    # archived → published taqiqlangan (avval draft ga qaytish kerak).
    arch = await client.post(
        f"/api/v1/content/{item['id']}/publish",
        json={"status": "archived"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert arch.status_code == 200

    bad = await client.post(
        f"/api/v1/content/{item['id']}/publish",
        json={"status": "published"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert bad.status_code == 422


# ----------------------------------------------------------------------------
# List filters
# ----------------------------------------------------------------------------


async def test_list_filter_by_type_and_status(client: AsyncClient) -> None:
    token = await _teacher(client)
    a = await _create_text(client, token, "Item A draft")
    b = await _create_text(client, token, "Item B published")
    await client.post(
        f"/api/v1/content/{b['id']}/publish",
        json={"status": "published"},
        headers={"Authorization": f"Bearer {token}"},
    )

    r = await client.get(
        "/api/v1/content?status=draft&type=text",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    ids = [i["id"] for i in r.json()["items"]]
    assert a["id"] in ids
    assert b["id"] not in ids

    r2 = await client.get(
        "/api/v1/content?status=published",
        headers={"Authorization": f"Bearer {token}"},
    )
    ids2 = [i["id"] for i in r2.json()["items"]]
    assert b["id"] in ids2
    assert a["id"] not in ids2


async def test_list_search_by_title(client: AsyncClient) -> None:
    token = await _teacher(client)
    await _create_text(client, token, "Algoritmlar")
    await _create_text(client, token, "Tarix")

    r = await client.get(
        "/api/v1/content?q=algorit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    titles = [i["title"] for i in r.json()["items"]]
    assert any("Algoritmlar" in t for t in titles)
    assert all("Tarix" not in t for t in titles)


# ----------------------------------------------------------------------------
# Subject FK
# ----------------------------------------------------------------------------


async def test_create_with_invalid_subject_returns_404(client: AsyncClient) -> None:
    token = await _teacher(client)
    r = await client.post(
        "/api/v1/content",
        json={
            "type": "text",
            "title": "Bog'liq fan yo'q",
            "content_data": {"ops": []},
            "subject_id": 999_999,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


async def test_create_with_valid_subject(client: AsyncClient) -> None:
    admin = await _admin(client)
    teacher = await _teacher(client)
    h_admin = {"Authorization": f"Bearer {admin}"}

    org = (
        await client.post(
            "/api/v1/organizations",
            json={"code": "XIU", "name": "Test", "type": "private"},
            headers=h_admin,
        )
    ).json()
    fac = (
        await client.post(
            "/api/v1/faculties",
            json={"organization_id": org["id"], "code": "IT", "name": "AT"},
            headers=h_admin,
        )
    ).json()
    dep = (
        await client.post(
            "/api/v1/departments",
            json={"faculty_id": fac["id"], "code": "SE", "name": "Dasturiy injiniring"},
            headers=h_admin,
        )
    ).json()
    sub = (
        await client.post(
            "/api/v1/subjects",
            json={
                "department_id": dep["id"],
                "code": "CS101",
                "name": "Kompyuter ilmlari asoslari",
                "credits": 6,
            },
            headers=h_admin,
        )
    ).json()

    r = await client.post(
        "/api/v1/content",
        json={
            "type": "text",
            "title": "CS101 1-mavzu",
            "content_data": {"ops": [{"insert": "Kirish\n"}]},
            "subject_id": sub["id"],
        },
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["subject_id"] == sub["id"]

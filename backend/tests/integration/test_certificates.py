"""Phase 11d — Sertifikat smoke testlari.

Coverage:
  - Kurs 100% tugatilgan paytda sertifikat avtomatik beriladi
  - Idempotent — bir kurs uchun bitta sertifikat
  - GET /me/certificates — talaba o'z ro'yxati
  - GET /verify/{code} — PUBLIC, autentifikatsiyasiz
  - Noto'g'ri kod => valid=False
  - Boshqa user sertifikatiga 403
"""

from __future__ import annotations

import uuid

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete, select, text

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
from app.modules.certificates.models import Certificate
from app.modules.content.models import ContentItem
from app.modules.courses.models import (
    Course,
    Enrollment,
    Lesson,
    LessonProgress,
    Module,
)
from app.modules.organizations.models import Organization

VALID_PASSWORD = "Str0ng!Password"
TEACHER_EMAIL = "teacher@xiuedu.uz"
TEACHER_PASSWORD = "Teacher!2026"
STUDENT_EMAIL = "student@xiuedu.uz"
STUDENT_PASSWORD = "Student!2026"


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def clean_certificates():
    async with SessionLocal() as db:
        await db.execute(delete(Certificate))
        await db.execute(delete(LessonProgress))
        await db.execute(delete(Enrollment))
        await db.execute(delete(Lesson))
        await db.execute(delete(Module))
        await db.execute(delete(Course))
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


def _slug() -> str:
    return f"course-{uuid.uuid4().hex[:8]}"


async def _login(client: AsyncClient, email: str, password: str) -> str:
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


async def _setup_published_course_with_lesson(
    client: AsyncClient, teacher_token: str
) -> tuple[int, int]:
    h = {"Authorization": f"Bearer {teacher_token}"}
    r = await client.post(
        "/api/v1/courses",
        json={
            "title": "Sertifikat sinov kursi",
            "slug": _slug(),
            "type": "open",
            "language": "uz-lat",
            "enrollment_type": "self",
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    course_id = r.json()["id"]

    r = await client.post(
        f"/api/v1/courses/{course_id}/modules",
        json={"title": "Modul 1"},
        headers=h,
    )
    module_id = r.json()["id"]

    r = await client.post(
        f"/api/v1/modules/{module_id}/lessons",
        json={"title": "Yagona dars"},
        headers=h,
    )
    lesson_id = r.json()["id"]

    r = await client.post(f"/api/v1/courses/{course_id}/publish", headers=h)
    assert r.status_code == 200, r.text
    return course_id, lesson_id


# ----------------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------------


async def test_certificate_auto_issued_on_course_complete(
    client: AsyncClient,
) -> None:
    t_token = await _login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
    s_token = await _login(client, STUDENT_EMAIL, STUDENT_PASSWORD)
    course_id, lesson_id = await _setup_published_course_with_lesson(client, t_token)

    # Talaba enroll va darsni tugatadi
    r = await client.post(
        f"/api/v1/courses/{course_id}/enroll",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.status_code == 201, r.text

    r = await client.post(
        f"/api/v1/lessons/{lesson_id}/complete",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.status_code == 200, r.text

    # /me/certificates ro'yxatida bitta yozuv bo'lishi kerak
    r = await client.get(
        "/api/v1/me/certificates",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) == 1
    cert = items[0]
    assert cert["certificate_number"].startswith("XIU-")
    assert cert["revoked_at"] is None
    assert cert["verification_url"].endswith(cert["verification_url"].rsplit("/", 1)[-1])


async def test_certificate_is_idempotent(client: AsyncClient) -> None:
    t_token = await _login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
    s_token = await _login(client, STUDENT_EMAIL, STUDENT_PASSWORD)
    course_id, lesson_id = await _setup_published_course_with_lesson(client, t_token)
    await client.post(
        f"/api/v1/courses/{course_id}/enroll",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    await client.post(
        f"/api/v1/lessons/{lesson_id}/complete",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    # Yana bir marta complete
    r = await client.post(
        f"/api/v1/lessons/{lesson_id}/complete",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.status_code == 200

    async with SessionLocal() as db:
        rows = (
            await db.execute(
                select(Certificate).where(Certificate.course_id == course_id)
            )
        ).scalars().all()
        assert len(rows) == 1


async def test_public_verify_endpoint(client: AsyncClient) -> None:
    t_token = await _login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
    s_token = await _login(client, STUDENT_EMAIL, STUDENT_PASSWORD)
    course_id, lesson_id = await _setup_published_course_with_lesson(client, t_token)
    await client.post(
        f"/api/v1/courses/{course_id}/enroll",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    await client.post(
        f"/api/v1/lessons/{lesson_id}/complete",
        headers={"Authorization": f"Bearer {s_token}"},
    )

    # Sertifikatni topib verification_code'ni olamiz
    async with SessionLocal() as db:
        cert = (
            await db.execute(
                select(Certificate).where(Certificate.course_id == course_id)
            )
        ).scalar_one()
        code = cert.verification_code
        cert_number = cert.certificate_number

    # PUBLIC chaqiruv — autentifikatsiyasiz
    r = await client.get(f"/api/v1/verify/{code}")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["valid"] is True
    assert data["certificate_number"] == cert_number
    assert data["student_name"]
    assert data["course_title"]


async def test_invalid_code_returns_valid_false(client: AsyncClient) -> None:
    r = await client.get("/api/v1/verify/nonexistent12345")
    assert r.status_code == 200
    assert r.json() == {
        "valid": False,
        "certificate_number": None,
        "student_name": None,
        "course_title": None,
        "issued_at": None,
        "revoked_at": None,
        "revoke_reason": None,
        "score_percentage": None,
    }


async def test_cannot_access_other_users_cert(client: AsyncClient) -> None:
    t_token = await _login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
    s_token = await _login(client, STUDENT_EMAIL, STUDENT_PASSWORD)
    course_id, lesson_id = await _setup_published_course_with_lesson(client, t_token)
    await client.post(
        f"/api/v1/courses/{course_id}/enroll",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    await client.post(
        f"/api/v1/lessons/{lesson_id}/complete",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    async with SessionLocal() as db:
        cert = (
            await db.execute(
                select(Certificate).where(Certificate.course_id == course_id)
            )
        ).scalar_one()
        cid = cert.id

    # O'qituvchi (boshqa user) talaba sertifikatiga 403
    r = await client.get(
        f"/api/v1/me/certificates/{cid}",
        headers={"Authorization": f"Bearer {t_token}"},
    )
    assert r.status_code == 403

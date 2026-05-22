"""Phase 11c — Lesson comments smoke testlari.

Coverage:
  - Top-level izoh yozish (talaba kursga enroll bo'lgan)
  - 1 darajali reply (parent_comment_id)
  - Reply on reply => parent ko'tariladi (flat 1 level)
  - Like toggle
  - Tahrir (faqat muallif)
  - O'chirish (muallif yoki kurs o'qituvchisi)
  - Enroll bo'lmagan user => 403
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
from app.modules.communications.models import (
    LessonComment,
    LessonCommentLike,
)
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
async def clean_comments():
    async with SessionLocal() as db:
        await db.execute(delete(LessonCommentLike))
        await db.execute(delete(LessonComment))
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


def _email() -> str:
    return f"u_{uuid.uuid4().hex[:10]}@example.com"


def _slug() -> str:
    return f"course-{uuid.uuid4().hex[:8]}"


async def _login(client: AsyncClient, email: str, password: str) -> str:
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


async def _teacher(client: AsyncClient) -> str:
    return await _login(client, TEACHER_EMAIL, TEACHER_PASSWORD)


async def _student(client: AsyncClient) -> str:
    return await _login(client, STUDENT_EMAIL, STUDENT_PASSWORD)


async def _new_student(client: AsyncClient) -> str:
    email = _email()
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD, "full_name": "Test User"},
    )
    assert r.status_code == 201, r.text
    return await _login(client, email, VALID_PASSWORD)


async def _setup_course_lesson(
    client: AsyncClient, teacher_token: str
) -> tuple[int, int]:
    """Course + module + lesson yaratib (course_id, lesson_id) qaytaradi."""
    h = {"Authorization": f"Bearer {teacher_token}"}
    r = await client.post(
        "/api/v1/courses",
        json={
            "title": "Comments test kursi",
            "slug": _slug(),
            "type": "open",
            "language": "uz-lat",
            "enrollment_type": "self",
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    course = r.json()
    course_id = course["id"]

    r = await client.post(
        f"/api/v1/courses/{course_id}/modules",
        json={"title": "M1"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    module_id = r.json()["id"]

    r = await client.post(
        f"/api/v1/modules/{module_id}/lessons",
        json={"title": "Dars 1"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    lesson_id = r.json()["id"]

    # Publish — talaba enroll qila olishi uchun
    r = await client.post(
        f"/api/v1/courses/{course_id}/publish",
        headers=h,
    )
    assert r.status_code == 200, r.text

    return course_id, lesson_id


# ----------------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------------


async def test_enrolled_student_can_comment(client: AsyncClient) -> None:
    t_token = await _teacher(client)
    s_token = await _student(client)
    course_id, lesson_id = await _setup_course_lesson(client, t_token)

    # Talaba enroll
    r = await client.post(
        f"/api/v1/courses/{course_id}/enroll",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.status_code == 201

    # Top-level izoh
    r = await client.post(
        f"/api/v1/lessons/{lesson_id}/comments",
        json={"body": "Bu darsda eshikni unutib qoldingiz"},
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.status_code == 201, r.text
    c1 = r.json()
    assert c1["parent_comment_id"] is None

    # Reply (1 darajali)
    r = await client.post(
        f"/api/v1/lessons/{lesson_id}/comments",
        json={"body": "Aniqlandi, rahmat", "parent_comment_id": c1["id"]},
        headers={"Authorization": f"Bearer {t_token}"},
    )
    assert r.status_code == 201
    reply = r.json()
    assert reply["parent_comment_id"] == c1["id"]

    # Reply on reply — flat 1 level qoidasi tufayli parent oddiy parent'ga ko'tariladi
    r = await client.post(
        f"/api/v1/lessons/{lesson_id}/comments",
        json={"body": "Yaxshi", "parent_comment_id": reply["id"]},
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.status_code == 201
    deep_reply = r.json()
    assert deep_reply["parent_comment_id"] == c1["id"]

    # List
    r = await client.get(
        f"/api/v1/lessons/{lesson_id}/comments",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.status_code == 200
    assert r.json()["total"] == 3


async def test_non_enrolled_user_403(client: AsyncClient) -> None:
    t_token = await _teacher(client)
    other_token = await _new_student(client)
    _, lesson_id = await _setup_course_lesson(client, t_token)

    r = await client.get(
        f"/api/v1/lessons/{lesson_id}/comments",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert r.status_code == 403

    r = await client.post(
        f"/api/v1/lessons/{lesson_id}/comments",
        json={"body": "intruder"},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert r.status_code == 403


async def test_like_toggle(client: AsyncClient) -> None:
    t_token = await _teacher(client)
    s_token = await _student(client)
    course_id, lesson_id = await _setup_course_lesson(client, t_token)
    await client.post(
        f"/api/v1/courses/{course_id}/enroll",
        headers={"Authorization": f"Bearer {s_token}"},
    )

    r = await client.post(
        f"/api/v1/lessons/{lesson_id}/comments",
        json={"body": "Test"},
        headers={"Authorization": f"Bearer {s_token}"},
    )
    cid = r.json()["id"]

    r = await client.post(
        f"/api/v1/lessons/comments/{cid}/like",
        headers={"Authorization": f"Bearer {t_token}"},
    )
    assert r.status_code == 200
    assert r.json()["like_count"] == 1
    assert r.json()["liked_by_me"] is True

    r = await client.post(
        f"/api/v1/lessons/comments/{cid}/like",
        headers={"Authorization": f"Bearer {t_token}"},
    )
    assert r.status_code == 200
    assert r.json()["like_count"] == 0
    assert r.json()["liked_by_me"] is False


async def test_only_author_edits(client: AsyncClient) -> None:
    t_token = await _teacher(client)
    s_token = await _student(client)
    course_id, lesson_id = await _setup_course_lesson(client, t_token)
    await client.post(
        f"/api/v1/courses/{course_id}/enroll",
        headers={"Authorization": f"Bearer {s_token}"},
    )

    r = await client.post(
        f"/api/v1/lessons/{lesson_id}/comments",
        json={"body": "asl matn"},
        headers={"Authorization": f"Bearer {s_token}"},
    )
    cid = r.json()["id"]

    # O'qituvchi tahrirlay olmaydi (faqat muallif)
    r = await client.patch(
        f"/api/v1/lessons/comments/{cid}",
        json={"body": "hacked"},
        headers={"Authorization": f"Bearer {t_token}"},
    )
    assert r.status_code == 403

    # Muallif tahrirlay oladi
    r = await client.patch(
        f"/api/v1/lessons/comments/{cid}",
        json={"body": "yangi matn"},
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.status_code == 200
    assert r.json()["body"] == "yangi matn"
    assert r.json()["edited_at"] is not None


async def test_teacher_can_delete_any_comment(client: AsyncClient) -> None:
    t_token = await _teacher(client)
    s_token = await _student(client)
    course_id, lesson_id = await _setup_course_lesson(client, t_token)
    await client.post(
        f"/api/v1/courses/{course_id}/enroll",
        headers={"Authorization": f"Bearer {s_token}"},
    )

    r = await client.post(
        f"/api/v1/lessons/{lesson_id}/comments",
        json={"body": "spam"},
        headers={"Authorization": f"Bearer {s_token}"},
    )
    cid = r.json()["id"]

    # O'qituvchi (kurs muallifi) o'chirib bo'la oladi
    r = await client.delete(
        f"/api/v1/lessons/comments/{cid}",
        headers={"Authorization": f"Bearer {t_token}"},
    )
    assert r.status_code == 204

    # Endi ro'yxatda yo'q
    r = await client.get(
        f"/api/v1/lessons/{lesson_id}/comments",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.json()["total"] == 0

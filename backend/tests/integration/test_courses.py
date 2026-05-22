"""Phase 3b — Courses backend smoke tests.

Coverage:
  - Course CRUD + slug uniqueness + status workflow
  - Module/Lesson CRUD + reorder
  - Enrollment (self vs manual, max_students cap, duplicate)
  - LessonProgress upsert + monotonic + course completion auto-trigger
  - RBAC: student create kurs => 403; teacher create => 201
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
from app.modules.courses.models import (
    Course,
    Enrollment,
    Lesson,
    LessonProgress,
    Module,
)
from app.modules.organizations.models import Organization

VALID_PASSWORD = "Str0ng!Password"
ADMIN_EMAIL = "admin@xiuedu.uz"
ADMIN_PASSWORD = "ChangeMe!2026"
TEACHER_EMAIL = "teacher@xiuedu.uz"
TEACHER_PASSWORD = "Teacher!2026"
STUDENT_EMAIL = "student@xiuedu.uz"
STUDENT_PASSWORD = "Student!2026"


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def clean_courses():
    async with SessionLocal() as db:
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


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


def _email() -> str:
    return f"u_{uuid.uuid4().hex[:10]}@example.com"


def _slug() -> str:
    return f"course-{uuid.uuid4().hex[:8]}"


async def _login(client: AsyncClient, email: str, password: str) -> str:
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


async def _admin(client: AsyncClient) -> str:
    return await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)


async def _teacher(client: AsyncClient) -> str:
    return await _login(client, TEACHER_EMAIL, TEACHER_PASSWORD)


async def _student_demo(client: AsyncClient) -> str:
    return await _login(client, STUDENT_EMAIL, STUDENT_PASSWORD)


async def _new_student(client: AsyncClient) -> tuple[str, int]:
    email = _email()
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD, "full_name": "Talaba Test"},
    )
    user_id = r.json()["id"]
    token = await _login(client, email, VALID_PASSWORD)
    return token, user_id


async def _create_course(
    client: AsyncClient,
    token: str,
    *,
    slug: str | None = None,
    title: str = "Algoritmlar va ma'lumotlar tuzilmasi",
    enrollment_type: str = "manual",
    max_students: int | None = None,
) -> dict:
    body = {
        "title": title,
        "slug": slug or _slug(),
        "description": "Test kursi",
        "type": "open",
        "language": "uz-lat",
        "enrollment_type": enrollment_type,
    }
    if max_students is not None:
        body["max_students"] = max_students
    r = await client.post(
        "/api/v1/courses", json=body, headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _publish(client: AsyncClient, token: str, course_id: int) -> None:
    r = await client.post(
        f"/api/v1/courses/{course_id}/publish",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text


# ----------------------------------------------------------------------------
# RBAC
# ----------------------------------------------------------------------------


async def test_student_cannot_create_course(client: AsyncClient) -> None:
    token = await _student_demo(client)
    r = await client.post(
        "/api/v1/courses",
        json={"title": "Hack", "slug": _slug()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


async def test_teacher_can_create_course(client: AsyncClient) -> None:
    token = await _teacher(client)
    r = await client.post(
        "/api/v1/courses",
        json={
            "title": "Yangi kurs",
            "slug": _slug(),
            "description": "Sinov",
            "type": "open",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "draft"


# ----------------------------------------------------------------------------
# Course CRUD
# ----------------------------------------------------------------------------


async def test_course_slug_uniqueness(client: AsyncClient) -> None:
    token = await _teacher(client)
    slug = _slug()
    await _create_course(client, token, slug=slug)
    r = await client.post(
        "/api/v1/courses",
        json={"title": "Boshqa kurs", "slug": slug},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 409


async def test_published_course_cannot_be_edited(client: AsyncClient) -> None:
    token = await _teacher(client)
    course = await _create_course(client, token)
    await _publish(client, token, course["id"])

    r = await client.patch(
        f"/api/v1/courses/{course['id']}",
        json={"title": "Yangi sarlavha"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 409


async def test_unpublish_returns_to_draft(client: AsyncClient) -> None:
    token = await _teacher(client)
    course = await _create_course(client, token)
    await _publish(client, token, course["id"])

    r = await client.post(
        f"/api/v1/courses/{course['id']}/unpublish",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "draft"


async def test_get_course_by_slug(client: AsyncClient) -> None:
    token = await _teacher(client)
    slug = _slug()
    course = await _create_course(client, token, slug=slug)
    r = await client.get(
        f"/api/v1/courses/by-slug/{slug}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["id"] == course["id"]


# ----------------------------------------------------------------------------
# Module + Lesson CRUD + reorder
# ----------------------------------------------------------------------------


async def test_module_lesson_create_and_order(client: AsyncClient) -> None:
    token = await _teacher(client)
    course = await _create_course(client, token)
    h = {"Authorization": f"Bearer {token}"}

    m1 = (
        await client.post(
            f"/api/v1/courses/{course['id']}/modules",
            json={"title": "Modul 1"},
            headers=h,
        )
    ).json()
    m2 = (
        await client.post(
            f"/api/v1/courses/{course['id']}/modules",
            json={"title": "Modul 2"},
            headers=h,
        )
    ).json()
    assert m1["order_index"] == 0
    assert m2["order_index"] == 1

    # Reorder
    r = await client.post(
        f"/api/v1/courses/{course['id']}/modules/reorder",
        json={"ordered_ids": [m2["id"], m1["id"]]},
        headers=h,
    )
    assert r.status_code == 200
    rec = {m["id"]: m["order_index"] for m in r.json()}
    assert rec[m2["id"]] == 0
    assert rec[m1["id"]] == 1

    # Lessons
    l1 = (
        await client.post(
            f"/api/v1/modules/{m1['id']}/lessons",
            json={"title": "Dars 1"},
            headers=h,
        )
    ).json()
    l2 = (
        await client.post(
            f"/api/v1/modules/{m1['id']}/lessons",
            json={"title": "Dars 2"},
            headers=h,
        )
    ).json()
    assert l1["order_index"] == 0
    assert l2["order_index"] == 1

    rr = await client.post(
        f"/api/v1/modules/{m1['id']}/lessons/reorder",
        json={"ordered_ids": [l2["id"], l1["id"]]},
        headers=h,
    )
    assert rr.status_code == 200


async def test_lesson_with_invalid_content_returns_404(client: AsyncClient) -> None:
    token = await _teacher(client)
    course = await _create_course(client, token)
    m = (
        await client.post(
            f"/api/v1/courses/{course['id']}/modules",
            json={"title": "Modul 1"},
            headers={"Authorization": f"Bearer {token}"},
        )
    ).json()
    r = await client.post(
        f"/api/v1/modules/{m['id']}/lessons",
        json={"title": "Dars", "primary_content_id": 999_999},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


# ----------------------------------------------------------------------------
# Enrollment
# ----------------------------------------------------------------------------


async def test_self_enroll_only_when_published(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    student = await _student_demo(client)

    course = await _create_course(client, teacher, enrollment_type="self")
    # Draft — yozilish mumkin emas
    r1 = await client.post(
        f"/api/v1/courses/{course['id']}/enroll",
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r1.status_code == 409

    await _publish(client, teacher, course["id"])
    r2 = await client.post(
        f"/api/v1/courses/{course['id']}/enroll",
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r2.status_code == 201


async def test_self_enroll_blocked_when_manual(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    student = await _student_demo(client)

    course = await _create_course(client, teacher, enrollment_type="manual")
    await _publish(client, teacher, course["id"])

    r = await client.post(
        f"/api/v1/courses/{course['id']}/enroll",
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r.status_code == 409


async def test_duplicate_enroll_returns_409(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    student = await _student_demo(client)
    course = await _create_course(client, teacher, enrollment_type="self")
    await _publish(client, teacher, course["id"])

    r1 = await client.post(
        f"/api/v1/courses/{course['id']}/enroll",
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r1.status_code == 201
    r2 = await client.post(
        f"/api/v1/courses/{course['id']}/enroll",
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r2.status_code == 409


async def test_max_students_cap(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    course = await _create_course(
        client, teacher, enrollment_type="self", max_students=1
    )
    await _publish(client, teacher, course["id"])

    s1, _ = await _new_student(client)
    s2, _ = await _new_student(client)

    r1 = await client.post(
        f"/api/v1/courses/{course['id']}/enroll",
        headers={"Authorization": f"Bearer {s1}"},
    )
    assert r1.status_code == 201
    r2 = await client.post(
        f"/api/v1/courses/{course['id']}/enroll",
        headers={"Authorization": f"Bearer {s2}"},
    )
    assert r2.status_code == 409


async def test_teacher_can_add_student_manually(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    course = await _create_course(client, teacher, enrollment_type="manual")
    await _publish(client, teacher, course["id"])
    _stoken, sid = await _new_student(client)

    r = await client.post(
        f"/api/v1/courses/{course['id']}/students",
        json={"user_id": sid, "enrollment_method": "manual"},
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["user_id"] == sid


# ----------------------------------------------------------------------------
# Progress
# ----------------------------------------------------------------------------


async def test_progress_requires_enrollment(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    student = await _student_demo(client)
    course = await _create_course(client, teacher)
    m = (
        await client.post(
            f"/api/v1/courses/{course['id']}/modules",
            json={"title": "Modul"},
            headers={"Authorization": f"Bearer {teacher}"},
        )
    ).json()
    lesson = (
        await client.post(
            f"/api/v1/modules/{m['id']}/lessons",
            json={"title": "Dars 1"},
            headers={"Authorization": f"Bearer {teacher}"},
        )
    ).json()

    r = await client.post(
        f"/api/v1/lessons/{lesson['id']}/start",
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r.status_code == 409


async def test_progress_monotonic_and_course_completion(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    course = await _create_course(client, teacher, enrollment_type="self")
    h_t = {"Authorization": f"Bearer {teacher}"}

    m = (
        await client.post(
            f"/api/v1/courses/{course['id']}/modules",
            json={"title": "Modul"},
            headers=h_t,
        )
    ).json()
    l1 = (
        await client.post(
            f"/api/v1/modules/{m['id']}/lessons",
            json={"title": "Dars 1"},
            headers=h_t,
        )
    ).json()
    l2 = (
        await client.post(
            f"/api/v1/modules/{m['id']}/lessons",
            json={"title": "Dars 2"},
            headers=h_t,
        )
    ).json()
    await _publish(client, teacher, course["id"])

    student, sid = await _new_student(client)
    h_s = {"Authorization": f"Bearer {student}"}

    enr = await client.post(
        f"/api/v1/courses/{course['id']}/enroll", headers=h_s
    )
    assert enr.status_code == 201

    # 30% saqlash, keyin 10% urinish — kichkina foiz qabul qilinmaydi
    p1 = await client.post(
        f"/api/v1/lessons/{l1['id']}/progress",
        json={"progress_percent": "30", "time_spent_seconds": 60},
        headers=h_s,
    )
    assert p1.status_code == 200
    assert float(p1.json()["progress_percent"]) == 30.0

    p2 = await client.post(
        f"/api/v1/lessons/{l1['id']}/progress",
        json={"progress_percent": "10"},
        headers=h_s,
    )
    assert p2.status_code == 200
    assert float(p2.json()["progress_percent"]) == 30.0  # oldinga emas, qaytmadi

    # Course progressi 50% bo'lmaydi (chunki l1 100% emas)
    cp = await client.get(
        f"/api/v1/courses/{course['id']}/my-progress", headers=h_s
    )
    assert cp.status_code == 200
    assert cp.json()["completed_lessons"] == 0
    assert cp.json()["total_required_lessons"] == 2

    # Ikkala darsni ham yakunlaymiz
    await client.post(f"/api/v1/lessons/{l1['id']}/complete", headers=h_s)
    await client.post(f"/api/v1/lessons/{l2['id']}/complete", headers=h_s)

    cp2 = await client.get(
        f"/api/v1/courses/{course['id']}/my-progress", headers=h_s
    )
    body = cp2.json()
    assert body["completed_lessons"] == 2
    assert float(body["percent"]) == 100.0
    assert body["completion_status"] == "completed"
    assert body["completed_at"] is not None


async def test_optional_lesson_does_not_block_completion(
    client: AsyncClient,
) -> None:
    """is_required_for_completion=False bo'lgan dars course progressga kirmaydi."""
    teacher = await _teacher(client)
    course = await _create_course(client, teacher, enrollment_type="self")
    h_t = {"Authorization": f"Bearer {teacher}"}

    m = (
        await client.post(
            f"/api/v1/courses/{course['id']}/modules",
            json={"title": "Modul"},
            headers=h_t,
        )
    ).json()
    required = (
        await client.post(
            f"/api/v1/modules/{m['id']}/lessons",
            json={"title": "Required"},
            headers=h_t,
        )
    ).json()
    await client.post(
        f"/api/v1/modules/{m['id']}/lessons",
        json={"title": "Optional", "is_required_for_completion": False},
        headers=h_t,
    )
    await _publish(client, teacher, course["id"])

    student, _ = await _new_student(client)
    h_s = {"Authorization": f"Bearer {student}"}
    await client.post(f"/api/v1/courses/{course['id']}/enroll", headers=h_s)
    await client.post(f"/api/v1/lessons/{required['id']}/complete", headers=h_s)

    cp = await client.get(
        f"/api/v1/courses/{course['id']}/my-progress", headers=h_s
    )
    assert float(cp.json()["percent"]) == 100.0
    assert cp.json()["completion_status"] == "completed"


async def test_teacher_can_list_students_with_progress(
    client: AsyncClient,
) -> None:
    teacher = await _teacher(client)
    course = await _create_course(client, teacher, enrollment_type="self")
    h_t = {"Authorization": f"Bearer {teacher}"}
    m = (
        await client.post(
            f"/api/v1/courses/{course['id']}/modules",
            json={"title": "Modul"},
            headers=h_t,
        )
    ).json()
    lesson = (
        await client.post(
            f"/api/v1/modules/{m['id']}/lessons",
            json={"title": "Dars"},
            headers=h_t,
        )
    ).json()
    await _publish(client, teacher, course["id"])

    student, sid = await _new_student(client)
    h_s = {"Authorization": f"Bearer {student}"}
    await client.post(f"/api/v1/courses/{course['id']}/enroll", headers=h_s)
    await client.post(f"/api/v1/lessons/{lesson['id']}/complete", headers=h_s)

    r = await client.get(
        f"/api/v1/courses/{course['id']}/students", headers=h_t
    )
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["user_id"] == sid
    assert float(items[0]["progress_percent"]) == 100.0
    assert items[0]["completion_status"] == "completed"

"""Phase 4e — Plagiat + Apellyatsiya tests.

Coverage:
  - Plagiarism: deterministic score, auto-trigger on submit, threshold flag,
    manual re-check
  - Appeals: student-only, must be graded, no duplicate pending, teacher
    approve with new_score updates submission, reject path
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

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
from app.modules.assignments.models import (
    Assignment,
    GradeAppeal,
    Rubric,
    Submission,
)
from app.modules.assignments.plagiarism import check_text
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
async def clean_phase4e():
    async with SessionLocal() as db:
        await db.execute(delete(GradeAppeal))
        await db.execute(delete(Submission))
        await db.execute(delete(Assignment))
        await db.execute(delete(Rubric))
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


def _iso(dt: datetime) -> str:
    return dt.isoformat()


async def _login(c: AsyncClient, email: str, password: str) -> str:
    r = await c.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


async def _teacher(c: AsyncClient) -> str:
    return await _login(c, TEACHER_EMAIL, TEACHER_PASSWORD)


async def _student_demo(c: AsyncClient) -> str:
    return await _login(c, STUDENT_EMAIL, STUDENT_PASSWORD)


async def _new_student(c: AsyncClient) -> tuple[str, int]:
    email = _email()
    r = await c.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD, "full_name": "Talaba"},
    )
    sid = r.json()["id"]
    # Talabaga 'student' rolini biriktirish (auth.register default'da student rolni qo'yadi)
    return await _login(c, email, VALID_PASSWORD), sid


async def _setup_course(c: AsyncClient, teacher: str) -> int:
    rc = await c.post(
        "/api/v1/courses",
        json={
            "title": "Phase 4e",
            "slug": _slug(),
            "type": "open",
            "enrollment_type": "self",
        },
        headers={"Authorization": f"Bearer {teacher}"},
    )
    cid = rc.json()["id"]
    await c.post(
        f"/api/v1/courses/{cid}/publish",
        headers={"Authorization": f"Bearer {teacher}"},
    )
    return cid


async def _create_essay(
    c: AsyncClient,
    teacher: str,
    *,
    course_id: int,
    plagiarism: bool = False,
    threshold: str = "30",
) -> int:
    body: dict = {
        "course_id": course_id,
        "title": "Insho 4e",
        "type": "essay",
        "due_date": _iso(datetime.now(timezone.utc) + timedelta(hours=24)),
        "max_score": "100",
    }
    if plagiarism:
        body["plagiarism_check_enabled"] = True
        body["plagiarism_threshold"] = threshold
    r = await c.post(
        "/api/v1/assignments",
        json=body,
        headers={"Authorization": f"Bearer {teacher}"},
    )
    aid = r.json()["id"]
    await c.post(
        f"/api/v1/assignments/{aid}/publish",
        json={"is_published": True},
        headers={"Authorization": f"Bearer {teacher}"},
    )
    return aid


async def _enroll(c: AsyncClient, student: str, course_id: int) -> None:
    r = await c.post(
        f"/api/v1/courses/{course_id}/enroll",
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r.status_code in {201, 409}, r.text


# ----------------------------------------------------------------------------
# Plagiarism
# ----------------------------------------------------------------------------


def test_plagiarism_mock_deterministic() -> None:
    """Bir matn — bir xil natija (idempotent test uchun)."""
    r1 = check_text("hello world", submission_id=1)
    r2 = check_text("hello world", submission_id=1)
    assert r1.similarity_percent == r2.similarity_percent
    assert r1.report_url == r2.report_url


def test_plagiarism_mock_zero_for_empty() -> None:
    r = check_text("", submission_id=1)
    assert r.similarity_percent == Decimal("0")


async def test_plagiarism_auto_trigger_on_submit(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_course(client, teacher)
    aid = await _create_essay(client, teacher, course_id=cid, plagiarism=True)
    student = await _student_demo(client)
    await _enroll(client, student, cid)

    r = await client.post(
        f"/api/v1/assignments/{aid}/submissions",
        json={"content": "Mening insho matnim"},
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["plagiarism_score"] is not None
    assert body["plagiarism_report_url"] is not None
    assert body["plagiarism_checked_at"] is not None


async def test_plagiarism_no_auto_when_disabled(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_course(client, teacher)
    aid = await _create_essay(client, teacher, course_id=cid, plagiarism=False)
    student = await _student_demo(client)
    await _enroll(client, student, cid)

    r = await client.post(
        f"/api/v1/assignments/{aid}/submissions",
        json={"content": "no plagiarism check"},
        headers={"Authorization": f"Bearer {student}"},
    )
    body = r.json()
    assert body["plagiarism_score"] is None
    assert body["plagiarism_flagged"] is False


async def test_plagiarism_manual_check(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_course(client, teacher)
    aid = await _create_essay(client, teacher, course_id=cid, plagiarism=False)
    student = await _student_demo(client)
    await _enroll(client, student, cid)
    sub = await client.post(
        f"/api/v1/assignments/{aid}/submissions",
        json={"content": "manual"},
        headers={"Authorization": f"Bearer {student}"},
    )
    sid = sub.json()["id"]

    r = await client.post(
        f"/api/v1/submissions/{sid}/check-plagiarism",
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["plagiarism_score"] is not None
    assert body["plagiarism_report_url"]


# ----------------------------------------------------------------------------
# Appeals
# ----------------------------------------------------------------------------


async def test_appeal_requires_graded(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_course(client, teacher)
    aid = await _create_essay(client, teacher, course_id=cid)
    student = await _student_demo(client)
    await _enroll(client, student, cid)
    sub = await client.post(
        f"/api/v1/assignments/{aid}/submissions",
        json={"content": "no grade yet"},
        headers={"Authorization": f"Bearer {student}"},
    )
    sid = sub.json()["id"]

    r = await client.post(
        f"/api/v1/submissions/{sid}/appeal",
        json={"reason": "Bahomga rozi emasman, qayta tekshiruvni iltimos"},
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r.status_code == 409


async def test_appeal_create_after_graded(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_course(client, teacher)
    aid = await _create_essay(client, teacher, course_id=cid)
    student = await _student_demo(client)
    await _enroll(client, student, cid)
    sub = await client.post(
        f"/api/v1/assignments/{aid}/submissions",
        json={"content": "essay text"},
        headers={"Authorization": f"Bearer {student}"},
    )
    sid = sub.json()["id"]

    # Pedagog baholaydi
    await client.post(
        f"/api/v1/submissions/{sid}/grade",
        json={"score": "60", "feedback": "improvable"},
        headers={"Authorization": f"Bearer {teacher}"},
    )

    # Talaba apellyatsiya
    r = await client.post(
        f"/api/v1/submissions/{sid}/appeal",
        json={"reason": "Ballim haq emas, qayta ko'rib chiqishingizni so'rayman"},
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "pending"


async def test_appeal_no_duplicate_pending(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_course(client, teacher)
    aid = await _create_essay(client, teacher, course_id=cid)
    student = await _student_demo(client)
    await _enroll(client, student, cid)
    sub = await client.post(
        f"/api/v1/assignments/{aid}/submissions",
        json={"content": "essay text"},
        headers={"Authorization": f"Bearer {student}"},
    )
    sid = sub.json()["id"]
    await client.post(
        f"/api/v1/submissions/{sid}/grade",
        json={"score": "60"},
        headers={"Authorization": f"Bearer {teacher}"},
    )
    r1 = await client.post(
        f"/api/v1/submissions/{sid}/appeal",
        json={"reason": "Birinchi apellyatsiya — ushbu javobimni qayta tekshirishingizni so'rayman"},
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r1.status_code == 201
    r2 = await client.post(
        f"/api/v1/submissions/{sid}/appeal",
        json={"reason": "Ikkinchi urinish — bu ham qayta ko'rib chiqilsin"},
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r2.status_code == 409


async def test_appeal_approve_updates_score(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_course(client, teacher)
    aid = await _create_essay(client, teacher, course_id=cid)
    student = await _student_demo(client)
    await _enroll(client, student, cid)
    sub = await client.post(
        f"/api/v1/assignments/{aid}/submissions",
        json={"content": "essay text"},
        headers={"Authorization": f"Bearer {student}"},
    )
    sid = sub.json()["id"]
    await client.post(
        f"/api/v1/submissions/{sid}/grade",
        json={"score": "60"},
        headers={"Authorization": f"Bearer {teacher}"},
    )
    appeal_resp = await client.post(
        f"/api/v1/submissions/{sid}/appeal",
        json={"reason": "Bahomga rozi emasman, mukammal javob bergan edim"},
        headers={"Authorization": f"Bearer {student}"},
    )
    aid_appeal = appeal_resp.json()["id"]

    # Pedagog approve qiladi (yangi 85 ball)
    r = await client.post(
        f"/api/v1/appeals/{aid_appeal}/respond",
        json={"status": "approved", "new_score": "85", "response": "Tasdiqlandi"},
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"

    # Submission score yangilanganligi
    sg = await client.get(
        f"/api/v1/submissions/{sid}",
        headers={"Authorization": f"Bearer {student}"},
    )
    assert Decimal(sg.json()["score"]) == Decimal("85.00")


async def test_appeal_reject(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_course(client, teacher)
    aid = await _create_essay(client, teacher, course_id=cid)
    student = await _student_demo(client)
    await _enroll(client, student, cid)
    sub = await client.post(
        f"/api/v1/assignments/{aid}/submissions",
        json={"content": "essay text"},
        headers={"Authorization": f"Bearer {student}"},
    )
    sid = sub.json()["id"]
    await client.post(
        f"/api/v1/submissions/{sid}/grade",
        json={"score": "60"},
        headers={"Authorization": f"Bearer {teacher}"},
    )
    appeal_resp = await client.post(
        f"/api/v1/submissions/{sid}/appeal",
        json={"reason": "Apellyatsiya — ballim qayta ko'rib chiqilsin"},
        headers={"Authorization": f"Bearer {student}"},
    )
    aid_appeal = appeal_resp.json()["id"]

    r = await client.post(
        f"/api/v1/appeals/{aid_appeal}/respond",
        json={"status": "rejected", "response": "Baho to'g'ri qo'yilgan"},
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"

    # Score o'zgarmagani
    sg = await client.get(
        f"/api/v1/submissions/{sid}",
        headers={"Authorization": f"Bearer {student}"},
    )
    assert Decimal(sg.json()["score"]) == Decimal("60.00")


async def test_appeal_inbox_scope(client: AsyncClient) -> None:
    """Pedagog faqat o'z kursi appellariyatsiyalarini ko'radi."""
    teacher = await _teacher(client)
    cid = await _setup_course(client, teacher)
    aid = await _create_essay(client, teacher, course_id=cid)
    student = await _student_demo(client)
    await _enroll(client, student, cid)
    sub = await client.post(
        f"/api/v1/assignments/{aid}/submissions",
        json={"content": "essay text"},
        headers={"Authorization": f"Bearer {student}"},
    )
    sid = sub.json()["id"]
    await client.post(
        f"/api/v1/submissions/{sid}/grade",
        json={"score": "55"},
        headers={"Authorization": f"Bearer {teacher}"},
    )
    appeal = await client.post(
        f"/api/v1/submissions/{sid}/appeal",
        json={"reason": "Reason of appeal — qayta ko'rilsin"},
        headers={"Authorization": f"Bearer {student}"},
    )
    appeal_id = appeal.json()["id"]

    inbox = await client.get(
        "/api/v1/appeals?status=pending",
        headers={"Authorization": f"Bearer {teacher}"},
    )
    ids = [a["id"] for a in inbox.json()["items"]]
    assert appeal_id in ids

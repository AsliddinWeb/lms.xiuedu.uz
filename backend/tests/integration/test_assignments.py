"""Phase 4a — Assignment + Submission backend smoke tests.

Coverage:
  - RBAC: student create assignment 403; teacher create 201
  - Assignment CRUD + publish workflow
  - Submission flow:
    - Must be published
    - Must be enrolled
    - Type 'essay' requires content; 'file' requires files
    - max_attempts cheklov
    - Late detection (is_late + days_late)
    - late_submission_allowed=False rejection
    - closed_at past => rejection
    - Pending attempt blocks new submit
  - Schema validation: due_date/closed_at/pass_score consistency
  - List filters: course_id, only_active
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

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
from app.modules.assignments.models import Assignment, Submission
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
async def clean_assignments():
    async with SessionLocal() as db:
        await db.execute(delete(Submission))
        await db.execute(delete(Assignment))
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
    return await _login(client, email, VALID_PASSWORD), user_id


async def _setup_published_course(
    client: AsyncClient, teacher: str, *, enrollment_type: str = "self"
) -> int:
    """Pedagog uchun published self-enroll kurs yaratadi va kurs id qaytaradi."""
    rc = await client.post(
        "/api/v1/courses",
        json={
            "title": "Topshiriq smoke kursi",
            "slug": _slug(),
            "type": "open",
            "enrollment_type": enrollment_type,
        },
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert rc.status_code == 201, rc.text
    cid = rc.json()["id"]
    rp = await client.post(
        f"/api/v1/courses/{cid}/publish",
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert rp.status_code == 200
    return cid


async def _enroll_student(
    client: AsyncClient, student: str, course_id: int
) -> None:
    r = await client.post(
        f"/api/v1/courses/{course_id}/enroll",
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r.status_code == 201, r.text


def _due(hours: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=hours)


# ----------------------------------------------------------------------------
# RBAC
# ----------------------------------------------------------------------------


async def test_student_cannot_create_assignment(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_published_course(client, teacher)
    student = await _student_demo(client)
    r = await client.post(
        "/api/v1/assignments",
        json={
            "course_id": cid,
            "title": "Hack",
            "type": "essay",
            "due_date": _iso(_due(24)),
        },
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r.status_code == 403


async def test_teacher_can_create_assignment(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_published_course(client, teacher)
    r = await client.post(
        "/api/v1/assignments",
        json={
            "course_id": cid,
            "title": "Birinchi insho",
            "description": "5-paragraf insho yozing",
            "type": "essay",
            "due_date": _iso(_due(24)),
            "max_score": "100",
            "max_attempts": 2,
        },
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["type"] == "essay"
    assert body["is_published"] is False
    assert body["max_attempts"] == 2


async def test_non_author_teacher_cannot_create(client: AsyncClient) -> None:
    """Pedagog faqat o'zi muallifi bo'lgan kursga assignment qo'sha oladi."""
    # Demo teacher kurs yaratadi
    teacher = await _teacher(client)
    cid = await _setup_published_course(client, teacher)

    # Boshqa user — assignment.manage permissioni yo'q
    other_token, _ = await _new_student(client)
    r = await client.post(
        "/api/v1/assignments",
        json={
            "course_id": cid,
            "title": "Talaba urinishi",
            "type": "essay",
            "due_date": _iso(_due(24)),
        },
        headers={"Authorization": f"Bearer {other_token}"},
    )
    # Talabada assignment.manage permissioni yo'q → 403
    assert r.status_code == 403


# ----------------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------------


async def test_due_before_available_rejected(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_published_course(client, teacher)
    r = await client.post(
        "/api/v1/assignments",
        json={
            "course_id": cid,
            "title": "Buzilgan sana",
            "type": "essay",
            "available_from": _iso(_due(48)),
            "due_date": _iso(_due(24)),
        },
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 422


async def test_pass_score_above_max_rejected(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_published_course(client, teacher)
    r = await client.post(
        "/api/v1/assignments",
        json={
            "course_id": cid,
            "title": "Buzilgan baho",
            "type": "essay",
            "due_date": _iso(_due(24)),
            "max_score": "50",
            "pass_score": "60",
        },
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 422


# ----------------------------------------------------------------------------
# Publish workflow
# ----------------------------------------------------------------------------


async def test_publish_toggle(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_published_course(client, teacher)
    r = await client.post(
        "/api/v1/assignments",
        json={
            "course_id": cid,
            "title": "Publish test",
            "type": "essay",
            "due_date": _iso(_due(24)),
        },
        headers={"Authorization": f"Bearer {teacher}"},
    )
    aid = r.json()["id"]

    pub = await client.post(
        f"/api/v1/assignments/{aid}/publish",
        json={"is_published": True},
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert pub.status_code == 200
    assert pub.json()["is_published"] is True

    unpub = await client.post(
        f"/api/v1/assignments/{aid}/publish",
        json={"is_published": False},
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert unpub.json()["is_published"] is False


# ----------------------------------------------------------------------------
# Submission flow
# ----------------------------------------------------------------------------


async def _create_published_essay(
    client: AsyncClient,
    teacher: str,
    *,
    course_id: int,
    due_hours: int = 24,
    max_attempts: int = 1,
    late_allowed: bool = True,
    closed_in_hours: int | None = None,
) -> int:
    body = {
        "course_id": course_id,
        "title": "Insho",
        "type": "essay",
        "due_date": _iso(_due(due_hours)),
        "max_attempts": max_attempts,
        "late_submission_allowed": late_allowed,
    }
    if closed_in_hours is not None:
        body["closed_at"] = _iso(_due(closed_in_hours))
    r = await client.post(
        "/api/v1/assignments",
        json=body,
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    pub = await client.post(
        f"/api/v1/assignments/{aid}/publish",
        json={"is_published": True},
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert pub.status_code == 200
    return aid


async def test_submit_requires_published(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_published_course(client, teacher)
    student = await _student_demo(client)
    await _enroll_student(client, student, cid)

    r = await client.post(
        "/api/v1/assignments",
        json={
            "course_id": cid,
            "title": "Yopiq",
            "type": "essay",
            "due_date": _iso(_due(24)),
        },
        headers={"Authorization": f"Bearer {teacher}"},
    )
    aid = r.json()["id"]
    # is_published=False bilan submit
    rs = await client.post(
        f"/api/v1/assignments/{aid}/submissions",
        json={"content": "Mening javobim"},
        headers={"Authorization": f"Bearer {student}"},
    )
    assert rs.status_code == 409


async def test_submit_requires_enrollment(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_published_course(client, teacher)
    aid = await _create_published_essay(client, teacher, course_id=cid)

    student = await _student_demo(client)
    # Hech qaysi kursga yozilmagan
    rs = await client.post(
        f"/api/v1/assignments/{aid}/submissions",
        json={"content": "Mening javobim"},
        headers={"Authorization": f"Bearer {student}"},
    )
    assert rs.status_code == 403


async def test_submit_essay_requires_content(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_published_course(client, teacher)
    aid = await _create_published_essay(client, teacher, course_id=cid)
    student = await _student_demo(client)
    await _enroll_student(client, student, cid)

    # content + files ikkalasi ham bo'sh — schema 422
    r = await client.post(
        f"/api/v1/assignments/{aid}/submissions",
        json={"content": "", "files": []},
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r.status_code == 422


async def test_submit_file_requires_files(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_published_course(client, teacher)
    # type=file
    r = await client.post(
        "/api/v1/assignments",
        json={
            "course_id": cid,
            "title": "Hujjat yuklash",
            "type": "file",
            "due_date": _iso(_due(24)),
        },
        headers={"Authorization": f"Bearer {teacher}"},
    )
    aid = r.json()["id"]
    await client.post(
        f"/api/v1/assignments/{aid}/publish",
        json={"is_published": True},
        headers={"Authorization": f"Bearer {teacher}"},
    )

    student = await _student_demo(client)
    await _enroll_student(client, student, cid)

    # Faqat content bilan submit — file turida content yetmaydi
    r = await client.post(
        f"/api/v1/assignments/{aid}/submissions",
        json={"content": "Sarlavha"},
        headers={"Authorization": f"Bearer {student}"},
    )
    # ValidationError 422
    assert r.status_code == 422


async def test_submit_essay_creates_submission(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_published_course(client, teacher)
    aid = await _create_published_essay(client, teacher, course_id=cid, max_attempts=2)
    student = await _student_demo(client)
    await _enroll_student(client, student, cid)

    r = await client.post(
        f"/api/v1/assignments/{aid}/submissions",
        json={"content": "Birinchi javobim"},
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["attempt_number"] == 1
    assert body["status"] == "submitted"
    assert body["is_late"] is False
    assert body["days_late"] == 0
    assert body["score"] is None


async def test_max_attempts_exceeded(client: AsyncClient) -> None:
    """Pedagog tomonida grading bo'lmasdan ham agar attempt 'submitted' bo'lsa,
    keyingisini blok qiladi (pending attempt blocks)."""
    teacher = await _teacher(client)
    cid = await _setup_published_course(client, teacher)
    aid = await _create_published_essay(client, teacher, course_id=cid, max_attempts=1)
    student = await _student_demo(client)
    await _enroll_student(client, student, cid)

    r1 = await client.post(
        f"/api/v1/assignments/{aid}/submissions",
        json={"content": "1"},
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r1.status_code == 201

    r2 = await client.post(
        f"/api/v1/assignments/{aid}/submissions",
        json={"content": "2"},
        headers={"Authorization": f"Bearer {student}"},
    )
    # Kutilayotgan urinish bor — 409
    assert r2.status_code == 409


async def test_closed_at_past_rejects(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_published_course(client, teacher)
    # closed_at o'tgan — lekin schema due_date < closed_at talab qiladi
    # Shu sabab due_date ni ham o'tgan vaqtga qo'yamiz
    r = await client.post(
        "/api/v1/assignments",
        json={
            "course_id": cid,
            "title": "Yopilgan",
            "type": "essay",
            "due_date": _iso(datetime.now(timezone.utc) - timedelta(hours=2)),
            "closed_at": _iso(datetime.now(timezone.utc) - timedelta(hours=1)),
            "late_submission_allowed": True,
        },
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 201
    aid = r.json()["id"]
    await client.post(
        f"/api/v1/assignments/{aid}/publish",
        json={"is_published": True},
        headers={"Authorization": f"Bearer {teacher}"},
    )

    student = await _student_demo(client)
    await _enroll_student(client, student, cid)

    rs = await client.post(
        f"/api/v1/assignments/{aid}/submissions",
        json={"content": "Kech keldim"},
        headers={"Authorization": f"Bearer {student}"},
    )
    assert rs.status_code == 409


async def test_late_submission_blocked_when_disabled(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_published_course(client, teacher)
    # due_date o'tgan + late_submission_allowed=False
    r = await client.post(
        "/api/v1/assignments",
        json={
            "course_id": cid,
            "title": "Strict",
            "type": "essay",
            "due_date": _iso(datetime.now(timezone.utc) - timedelta(hours=1)),
            "late_submission_allowed": False,
        },
        headers={"Authorization": f"Bearer {teacher}"},
    )
    aid = r.json()["id"]
    await client.post(
        f"/api/v1/assignments/{aid}/publish",
        json={"is_published": True},
        headers={"Authorization": f"Bearer {teacher}"},
    )
    student = await _student_demo(client)
    await _enroll_student(client, student, cid)

    rs = await client.post(
        f"/api/v1/assignments/{aid}/submissions",
        json={"content": "Kech"},
        headers={"Authorization": f"Bearer {student}"},
    )
    assert rs.status_code == 409


async def test_late_submission_marks_is_late(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_published_course(client, teacher)
    r = await client.post(
        "/api/v1/assignments",
        json={
            "course_id": cid,
            "title": "Late OK",
            "type": "essay",
            "due_date": _iso(datetime.now(timezone.utc) - timedelta(hours=2)),
            "late_submission_allowed": True,
            "late_penalty_per_day": "10",
        },
        headers={"Authorization": f"Bearer {teacher}"},
    )
    aid = r.json()["id"]
    await client.post(
        f"/api/v1/assignments/{aid}/publish",
        json={"is_published": True},
        headers={"Authorization": f"Bearer {teacher}"},
    )
    student = await _student_demo(client)
    await _enroll_student(client, student, cid)

    rs = await client.post(
        f"/api/v1/assignments/{aid}/submissions",
        json={"content": "Kech keldim"},
        headers={"Authorization": f"Bearer {student}"},
    )
    assert rs.status_code == 201
    body = rs.json()
    assert body["is_late"] is True
    assert body["days_late"] == 1


# ----------------------------------------------------------------------------
# Listing + access
# ----------------------------------------------------------------------------


async def test_teacher_lists_submissions(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_published_course(client, teacher)
    aid = await _create_published_essay(client, teacher, course_id=cid)

    student = await _student_demo(client)
    await _enroll_student(client, student, cid)
    await client.post(
        f"/api/v1/assignments/{aid}/submissions",
        json={"content": "Birinchi javobim"},
        headers={"Authorization": f"Bearer {student}"},
    )

    r = await client.get(
        f"/api/v1/assignments/{aid}/submissions",
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["content"] == "Birinchi javobim"


async def test_student_cannot_see_others_submission(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_published_course(client, teacher)
    aid = await _create_published_essay(client, teacher, course_id=cid)

    s1 = await _student_demo(client)
    await _enroll_student(client, s1, cid)
    sub_resp = await client.post(
        f"/api/v1/assignments/{aid}/submissions",
        json={"content": "S1 javobi"},
        headers={"Authorization": f"Bearer {s1}"},
    )
    sid = sub_resp.json()["id"]

    s2, _ = await _new_student(client)
    r = await client.get(
        f"/api/v1/submissions/{sid}",
        headers={"Authorization": f"Bearer {s2}"},
    )
    assert r.status_code == 403


async def test_mine_filter_returns_enrolled_courses_only(client: AsyncClient) -> None:
    """`?mine=true` faqat talaba yozilgan kurslar bo'yicha topshiriqlarni qaytaradi."""
    teacher = await _teacher(client)

    # 2 ta kurs yaratamiz, faqat birinchisiga student yoziladi
    cid1 = await _setup_published_course(client, teacher)
    cid2 = await _setup_published_course(client, teacher)

    aid_in = await _create_published_essay(client, teacher, course_id=cid1)
    aid_out = await _create_published_essay(client, teacher, course_id=cid2)

    student = await _student_demo(client)
    await _enroll_student(client, student, cid1)

    r = await client.get(
        "/api/v1/assignments?mine=true",
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r.status_code == 200
    ids = [a["id"] for a in r.json()["items"]]
    assert aid_in in ids
    assert aid_out not in ids


async def test_my_submissions_endpoint(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_published_course(client, teacher)
    aid = await _create_published_essay(
        client, teacher, course_id=cid, max_attempts=3
    )
    student = await _student_demo(client)
    await _enroll_student(client, student, cid)

    # 1 ta submission yaratish
    r1 = await client.post(
        f"/api/v1/assignments/{aid}/submissions",
        json={"content": "Birinchi"},
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r1.status_code == 201

    r = await client.get(
        f"/api/v1/assignments/{aid}/my-submissions",
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["attempt_number"] == 1


async def test_my_submissions_isolated_per_user(client: AsyncClient) -> None:
    """Boshqa talabaning submissionlari ko'rinmasligi."""
    teacher = await _teacher(client)
    cid = await _setup_published_course(client, teacher)
    aid = await _create_published_essay(client, teacher, course_id=cid)

    student1 = await _student_demo(client)
    await _enroll_student(client, student1, cid)
    await client.post(
        f"/api/v1/assignments/{aid}/submissions",
        json={"content": "S1"},
        headers={"Authorization": f"Bearer {student1}"},
    )

    student2, _ = await _new_student(client)
    r = await client.get(
        f"/api/v1/assignments/{aid}/my-submissions",
        headers={"Authorization": f"Bearer {student2}"},
    )
    assert r.status_code == 200
    assert r.json() == []


async def test_inbox_only_returns_my_courses(client: AsyncClient) -> None:
    """Pedagog inboxida boshqa kurslar (boshqa muallif) submissionlari yo'q."""
    teacher = await _teacher(client)
    cid = await _setup_published_course(client, teacher)
    aid = await _create_published_essay(client, teacher, course_id=cid)

    student = await _student_demo(client)
    await _enroll_student(client, student, cid)
    sub = await client.post(
        f"/api/v1/assignments/{aid}/submissions",
        json={"content": "T1 javob"},
        headers={"Authorization": f"Bearer {student}"},
    )
    sid = sub.json()["id"]

    inbox = await client.get(
        "/api/v1/submissions/inbox",
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert inbox.status_code == 200
    body = inbox.json()
    ids = [s["id"] for s in body["items"]]
    assert sid in ids


async def test_inbox_status_filter(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_published_course(client, teacher)
    aid = await _create_published_essay(client, teacher, course_id=cid)
    student = await _student_demo(client)
    await _enroll_student(client, student, cid)
    sub = await client.post(
        f"/api/v1/assignments/{aid}/submissions",
        json={"content": "OK"},
        headers={"Authorization": f"Bearer {student}"},
    )
    sid = sub.json()["id"]

    # status=submitted bo'yicha — bor
    r1 = await client.get(
        "/api/v1/submissions/inbox?status=submitted",
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert sid in [s["id"] for s in r1.json()["items"]]

    # status=graded bo'yicha — yo'q
    r2 = await client.get(
        "/api/v1/submissions/inbox?status=graded",
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert sid not in [s["id"] for s in r2.json()["items"]]


async def test_inbox_admin_sees_all(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_published_course(client, teacher)
    aid = await _create_published_essay(client, teacher, course_id=cid)
    student = await _student_demo(client)
    await _enroll_student(client, student, cid)
    sub = await client.post(
        f"/api/v1/assignments/{aid}/submissions",
        json={"content": "Admin scope test"},
        headers={"Authorization": f"Bearer {student}"},
    )
    sid = sub.json()["id"]

    admin = await _admin(client)
    inbox = await client.get(
        "/api/v1/submissions/inbox",
        headers={"Authorization": f"Bearer {admin}"},
    )
    assert sid in [s["id"] for s in inbox.json()["items"]]


async def test_only_active_filter_hides_unpublished(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_published_course(client, teacher)
    # Draft assignment
    r1 = await client.post(
        "/api/v1/assignments",
        json={
            "course_id": cid,
            "title": "Draft",
            "type": "essay",
            "due_date": _iso(_due(24)),
        },
        headers={"Authorization": f"Bearer {teacher}"},
    )
    draft_id = r1.json()["id"]
    # Published
    pub_id = await _create_published_essay(client, teacher, course_id=cid)

    student = await _student_demo(client)
    rls = await client.get(
        f"/api/v1/assignments?course_id={cid}&only_active=true",
        headers={"Authorization": f"Bearer {student}"},
    )
    ids = [a["id"] for a in rls.json()["items"]]
    assert pub_id in ids
    assert draft_id not in ids

"""Phase 4b — Rubric + Grading + Annotations tests.

Coverage:
  - Rubric CRUD + criteria validation (unique keys, level points <= max_points)
  - Assignment rubric_id biriktirish
  - Direct score grading (no rubric)
  - Rubric-based grading (rubric_scores → score auto-sum)
  - Late penalty applied to final_score
  - score > max_score rejected
  - Status transitions: submitted → graded / returned
  - Annotations save (full replace)
  - Cross-course teacher cannot grade
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
from app.modules.assignments.models import Assignment, Rubric, Submission
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
async def clean_grading():
    async with SessionLocal() as db:
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


async def _login(client: AsyncClient, email: str, password: str) -> str:
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


async def _teacher(client: AsyncClient) -> str:
    return await _login(client, TEACHER_EMAIL, TEACHER_PASSWORD)


async def _student_demo(client: AsyncClient) -> str:
    return await _login(client, STUDENT_EMAIL, STUDENT_PASSWORD)


async def _setup_course(
    client: AsyncClient, teacher_token: str, *, enrollment_type: str = "self"
) -> int:
    r = await client.post(
        "/api/v1/courses",
        json={
            "title": "Grading sinov kursi",
            "slug": _slug(),
            "type": "open",
            "enrollment_type": enrollment_type,
        },
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    cid = r.json()["id"]
    await client.post(
        f"/api/v1/courses/{cid}/publish",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    return cid


async def _enroll(client: AsyncClient, student_token: str, course_id: int) -> None:
    r = await client.post(
        f"/api/v1/courses/{course_id}/enroll",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert r.status_code == 201, r.text


async def _create_essay(
    client: AsyncClient,
    teacher_token: str,
    *,
    course_id: int,
    due_hours: int = 24,
    max_score: str = "100",
    late_penalty: str = "0",
    rubric_id: int | None = None,
) -> int:
    body: dict = {
        "course_id": course_id,
        "title": "Insho",
        "type": "essay",
        "due_date": _iso(datetime.now(timezone.utc) + timedelta(hours=due_hours)),
        "max_score": max_score,
        "late_penalty_per_day": late_penalty,
        "late_submission_allowed": True,
    }
    if rubric_id is not None:
        body["rubric_id"] = rubric_id
    r = await client.post(
        "/api/v1/assignments",
        json=body,
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    await client.post(
        f"/api/v1/assignments/{aid}/publish",
        json={"is_published": True},
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    return aid


async def _submit(
    client: AsyncClient,
    student_token: str,
    *,
    assignment_id: int,
    content: str = "Mening javobim",
) -> int:
    r = await client.post(
        f"/api/v1/assignments/{assignment_id}/submissions",
        json={"content": content},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ----------------------------------------------------------------------------
# Rubric CRUD + validation
# ----------------------------------------------------------------------------


async def test_rubric_create_and_total_calc(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    r = await client.post(
        "/api/v1/rubrics",
        json={
            "title": "Insho rubric",
            "criteria": [
                {"key": "structure", "name": "Tuzilish", "max_points": 30, "levels": []},
                {"key": "grammar", "name": "Grammatika", "max_points": 20, "levels": []},
                {"key": "argument", "name": "Argument", "max_points": 50, "levels": []},
            ],
        },
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert Decimal(body["total_points"]) == Decimal("100")
    assert len(body["criteria"]) == 3


async def test_rubric_duplicate_keys_rejected(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    r = await client.post(
        "/api/v1/rubrics",
        json={
            "title": "Buzilgan",
            "criteria": [
                {"key": "x", "name": "X", "max_points": 10},
                {"key": "x", "name": "X2", "max_points": 10},
            ],
        },
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 422


async def test_rubric_level_points_above_max_rejected(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    r = await client.post(
        "/api/v1/rubrics",
        json={
            "title": "Buzilgan level",
            "criteria": [
                {
                    "key": "structure",
                    "name": "Tuzilish",
                    "max_points": 20,
                    "levels": [{"label": "A'lo", "points": 30}],
                }
            ],
        },
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 422


async def test_rubric_update_recalculates_total(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    rc = await client.post(
        "/api/v1/rubrics",
        json={
            "title": "Boshlang'ich",
            "criteria": [{"key": "a", "name": "A", "max_points": 50}],
        },
        headers={"Authorization": f"Bearer {teacher}"},
    )
    rid = rc.json()["id"]
    upd = await client.patch(
        f"/api/v1/rubrics/{rid}",
        json={
            "criteria": [
                {"key": "a", "name": "A", "max_points": 30},
                {"key": "b", "name": "B", "max_points": 70},
            ]
        },
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert upd.status_code == 200
    assert Decimal(upd.json()["total_points"]) == Decimal("100")


async def test_student_cannot_create_rubric(client: AsyncClient) -> None:
    student = await _student_demo(client)
    r = await client.post(
        "/api/v1/rubrics",
        json={
            "title": "Hack",
            "criteria": [{"key": "a", "name": "A", "max_points": 10}],
        },
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r.status_code == 403


# ----------------------------------------------------------------------------
# Direct score grading
# ----------------------------------------------------------------------------


async def test_grade_direct_score(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_course(client, teacher)
    student = await _student_demo(client)
    await _enroll(client, student, cid)
    aid = await _create_essay(client, teacher, course_id=cid)
    sid = await _submit(client, student, assignment_id=aid)

    r = await client.post(
        f"/api/v1/submissions/{sid}/grade",
        json={"score": "85", "feedback": "Yaxshi", "grade_letter": "B"},
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert Decimal(body["score"]) == Decimal("85.00")
    assert Decimal(body["final_score"]) == Decimal("85.00")
    assert body["status"] == "graded"
    assert body["grade_letter"] == "B"
    assert body["feedback"] == "Yaxshi"
    assert body["graded_by"] is not None


async def test_grade_above_max_score_rejected(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_course(client, teacher)
    student = await _student_demo(client)
    await _enroll(client, student, cid)
    aid = await _create_essay(client, teacher, course_id=cid, max_score="50")
    sid = await _submit(client, student, assignment_id=aid)

    r = await client.post(
        f"/api/v1/submissions/{sid}/grade",
        json={"score": "60"},
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 422


async def test_grade_neither_score_nor_rubric(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_course(client, teacher)
    student = await _student_demo(client)
    await _enroll(client, student, cid)
    aid = await _create_essay(client, teacher, course_id=cid)
    sid = await _submit(client, student, assignment_id=aid)

    r = await client.post(
        f"/api/v1/submissions/{sid}/grade",
        json={"feedback": "no score"},
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 422


# ----------------------------------------------------------------------------
# Rubric-based grading
# ----------------------------------------------------------------------------


async def test_rubric_grading_sums_correctly(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    rc = await client.post(
        "/api/v1/rubrics",
        json={
            "title": "Insho",
            "criteria": [
                {"key": "structure", "name": "Tuzilish", "max_points": 30},
                {"key": "grammar", "name": "Grammatika", "max_points": 20},
                {"key": "argument", "name": "Argument", "max_points": 50},
            ],
        },
        headers={"Authorization": f"Bearer {teacher}"},
    )
    rid = rc.json()["id"]
    cid = await _setup_course(client, teacher)
    student = await _student_demo(client)
    await _enroll(client, student, cid)
    aid = await _create_essay(client, teacher, course_id=cid, rubric_id=rid)
    sid = await _submit(client, student, assignment_id=aid)

    r = await client.post(
        f"/api/v1/submissions/{sid}/grade",
        json={
            "rubric_scores": {"structure": 25, "grammar": 18, "argument": 40},
            "feedback": "Yaxshi argument",
        },
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert Decimal(body["score"]) == Decimal("83.00")
    assert Decimal(body["final_score"]) == Decimal("83.00")
    assert body["rubric_scores"] == {
        "structure": 25,
        "grammar": 18,
        "argument": 40,
    }


async def test_rubric_score_above_criterion_max_rejected(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    rc = await client.post(
        "/api/v1/rubrics",
        json={
            "title": "Mini rubric",
            "criteria": [{"key": "x", "name": "X", "max_points": 10}],
        },
        headers={"Authorization": f"Bearer {teacher}"},
    )
    rid = rc.json()["id"]
    cid = await _setup_course(client, teacher)
    student = await _student_demo(client)
    await _enroll(client, student, cid)
    aid = await _create_essay(client, teacher, course_id=cid, rubric_id=rid)
    sid = await _submit(client, student, assignment_id=aid)

    r = await client.post(
        f"/api/v1/submissions/{sid}/grade",
        json={"rubric_scores": {"x": 15}},
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 422


async def test_rubric_unknown_key_rejected(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    rc = await client.post(
        "/api/v1/rubrics",
        json={
            "title": "Mini rubric",
            "criteria": [{"key": "x", "name": "X", "max_points": 10}],
        },
        headers={"Authorization": f"Bearer {teacher}"},
    )
    rid = rc.json()["id"]
    cid = await _setup_course(client, teacher)
    student = await _student_demo(client)
    await _enroll(client, student, cid)
    aid = await _create_essay(client, teacher, course_id=cid, rubric_id=rid)
    sid = await _submit(client, student, assignment_id=aid)

    r = await client.post(
        f"/api/v1/submissions/{sid}/grade",
        json={"rubric_scores": {"unknown_key": 5}},
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 422


async def test_rubric_grading_requires_rubric_on_assignment(
    client: AsyncClient,
) -> None:
    """rubric_scores berilgan, ammo assignmentda rubric_id yo'q → 422"""
    teacher = await _teacher(client)
    cid = await _setup_course(client, teacher)
    student = await _student_demo(client)
    await _enroll(client, student, cid)
    aid = await _create_essay(client, teacher, course_id=cid)  # no rubric
    sid = await _submit(client, student, assignment_id=aid)

    r = await client.post(
        f"/api/v1/submissions/{sid}/grade",
        json={"rubric_scores": {"x": 5}},
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 422


# ----------------------------------------------------------------------------
# Late penalty
# ----------------------------------------------------------------------------


async def test_late_penalty_applies_to_final_score(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_course(client, teacher)
    student = await _student_demo(client)
    await _enroll(client, student, cid)

    # Topshiriq due_date 2 soat oldin → 1 kun late, 10% penalty
    r = await client.post(
        "/api/v1/assignments",
        json={
            "course_id": cid,
            "title": "Late penalty",
            "type": "essay",
            "due_date": _iso(datetime.now(timezone.utc) - timedelta(hours=2)),
            "late_submission_allowed": True,
            "late_penalty_per_day": "10",
            "max_score": "100",
        },
        headers={"Authorization": f"Bearer {teacher}"},
    )
    aid = r.json()["id"]
    await client.post(
        f"/api/v1/assignments/{aid}/publish",
        json={"is_published": True},
        headers={"Authorization": f"Bearer {teacher}"},
    )

    sid = await _submit(client, student, assignment_id=aid, content="Kech keldim")

    g = await client.post(
        f"/api/v1/submissions/{sid}/grade",
        json={"score": "100"},
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert g.status_code == 200
    body = g.json()
    assert Decimal(body["score"]) == Decimal("100.00")
    # 1 kun late × 10% = 10% penalty → final = 90
    assert Decimal(body["final_score"]) == Decimal("90.00")
    assert body["is_late"] is True
    assert body["days_late"] == 1


async def test_late_penalty_floor_at_zero(client: AsyncClient) -> None:
    """Penalty haddan ziyod bo'lsa final_score 0 ga tushadi (manfiy emas)."""
    teacher = await _teacher(client)
    cid = await _setup_course(client, teacher)
    student = await _student_demo(client)
    await _enroll(client, student, cid)

    # 5 kun late × 50% penalty per day → mantiqan -150% bo'lar edi, lekin 0 ga clamp
    r = await client.post(
        "/api/v1/assignments",
        json={
            "course_id": cid,
            "title": "Crushing penalty",
            "type": "essay",
            "due_date": _iso(datetime.now(timezone.utc) - timedelta(days=5, hours=1)),
            "late_submission_allowed": True,
            "late_penalty_per_day": "50",
        },
        headers={"Authorization": f"Bearer {teacher}"},
    )
    aid = r.json()["id"]
    await client.post(
        f"/api/v1/assignments/{aid}/publish",
        json={"is_published": True},
        headers={"Authorization": f"Bearer {teacher}"},
    )

    sid = await _submit(client, student, assignment_id=aid)
    g = await client.post(
        f"/api/v1/submissions/{sid}/grade",
        json={"score": "100"},
        headers={"Authorization": f"Bearer {teacher}"},
    )
    body = g.json()
    assert Decimal(body["final_score"]) == Decimal("0.00")


# ----------------------------------------------------------------------------
# Return for revision + status workflow
# ----------------------------------------------------------------------------


async def test_grade_with_return_sets_status_returned(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_course(client, teacher)
    student = await _student_demo(client)
    await _enroll(client, student, cid)
    aid = await _create_essay(client, teacher, course_id=cid)
    sid = await _submit(client, student, assignment_id=aid)

    r = await client.post(
        f"/api/v1/submissions/{sid}/grade",
        json={
            "score": "60",
            "feedback": "Qayta yozing",
            "return_for_revision": True,
        },
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "returned"


# ----------------------------------------------------------------------------
# Annotations
# ----------------------------------------------------------------------------


async def test_save_annotations(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    cid = await _setup_course(client, teacher)
    student = await _student_demo(client)
    await _enroll(client, student, cid)
    aid = await _create_essay(client, teacher, course_id=cid)
    sid = await _submit(client, student, assignment_id=aid)

    r = await client.put(
        f"/api/v1/submissions/{sid}/annotations",
        json={
            "annotations": [
                {"page": 1, "x": 10, "y": 20, "text": "Yaxshi paragraf"},
                {"page": 1, "text": "Diqqat: bu yerda xato bor", "color": "#dc2626"},
            ]
        },
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["annotations"]) == 2
    assert body["annotations"][1]["color"] == "#dc2626"


async def test_annotations_replace_full(client: AsyncClient) -> None:
    """PUT — to'liq almashtirish (eski annotationlar o'chadi)."""
    teacher = await _teacher(client)
    cid = await _setup_course(client, teacher)
    student = await _student_demo(client)
    await _enroll(client, student, cid)
    aid = await _create_essay(client, teacher, course_id=cid)
    sid = await _submit(client, student, assignment_id=aid)

    h = {"Authorization": f"Bearer {teacher}"}
    await client.put(
        f"/api/v1/submissions/{sid}/annotations",
        json={"annotations": [{"text": "1"}, {"text": "2"}]},
        headers=h,
    )
    r2 = await client.put(
        f"/api/v1/submissions/{sid}/annotations",
        json={"annotations": [{"text": "yagona"}]},
        headers=h,
    )
    assert len(r2.json()["annotations"]) == 1
    assert r2.json()["annotations"][0]["text"] == "yagona"


# ----------------------------------------------------------------------------
# Cross-course access
# ----------------------------------------------------------------------------


async def test_non_author_cannot_grade(client: AsyncClient) -> None:
    """Pedagog bo'lmagan boshqa user submissionga baho qo'ya olmaydi."""
    teacher = await _teacher(client)
    cid = await _setup_course(client, teacher)
    student = await _student_demo(client)
    await _enroll(client, student, cid)
    aid = await _create_essay(client, teacher, course_id=cid)
    sid = await _submit(client, student, assignment_id=aid)

    # Talaba o'z baholashga urinishi
    r = await client.post(
        f"/api/v1/submissions/{sid}/grade",
        json={"score": "100"},
        headers={"Authorization": f"Bearer {student}"},
    )
    # Talabada assignment.grade permissioni yo'q → 403
    assert r.status_code == 403

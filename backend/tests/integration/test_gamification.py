"""Phase 11e — Gamification smoke testlari.

Coverage:
  - Lesson complete => 5 ball + first_lesson badge
  - Kurs tugatilgan => course.completed event + first_course badge
  - Dedupe — bir xil event 2-marta yozilmaydi
  - Forum like => muallifga ball (o'zining post'iga emas)
  - /me/gamification stat endpoint
  - /gamification/leaderboard ro'yxat
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
from app.modules.communications.models import (
    ForumPost,
    ForumPostLike,
    ForumThread,
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
from app.modules.gamification.models import (
    GamificationEvent,
    UserBadge,
    UserPoints,
)
from app.modules.gamification.seed import seed_badges
from app.modules.organizations.models import Organization

TEACHER_EMAIL = "teacher@xiuedu.uz"
TEACHER_PASSWORD = "Teacher!2026"
STUDENT_EMAIL = "student@xiuedu.uz"
STUDENT_PASSWORD = "Student!2026"


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def clean_gamif():
    async with SessionLocal() as db:
        # Gamification jadvallari
        await db.execute(delete(UserBadge))
        await db.execute(delete(UserPoints))
        await db.execute(delete(GamificationEvent))
        # Bog'liq jadvallar
        await db.execute(delete(LessonCommentLike))
        await db.execute(delete(LessonComment))
        await db.execute(delete(ForumPostLike))
        await db.execute(delete(ForumPost))
        await db.execute(delete(ForumThread))
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
        # Badge katalogini qayta seed qilish (default 6 ta)
        await seed_badges(db)
        await db.commit()
    yield


def _slug() -> str:
    return f"course-{uuid.uuid4().hex[:8]}"


async def _login(client: AsyncClient, email: str, password: str) -> str:
    r = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


async def _setup_course_lesson(
    client: AsyncClient, teacher_token: str
) -> tuple[int, int]:
    h = {"Authorization": f"Bearer {teacher_token}"}
    r = await client.post(
        "/api/v1/courses",
        json={
            "title": "Gamif sinov kursi",
            "slug": _slug(),
            "type": "open",
            "language": "uz-lat",
            "enrollment_type": "self",
        },
        headers=h,
    )
    course_id = r.json()["id"]
    r = await client.post(
        f"/api/v1/courses/{course_id}/modules",
        json={"title": "M1"},
        headers=h,
    )
    module_id = r.json()["id"]
    r = await client.post(
        f"/api/v1/modules/{module_id}/lessons",
        json={"title": "Dars 1"},
        headers=h,
    )
    lesson_id = r.json()["id"]
    await client.post(f"/api/v1/courses/{course_id}/publish", headers=h)
    return course_id, lesson_id


# ----------------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------------


async def test_lesson_complete_awards_points_and_badge(client: AsyncClient) -> None:
    t_token = await _login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
    s_token = await _login(client, STUDENT_EMAIL, STUDENT_PASSWORD)
    course_id, lesson_id = await _setup_course_lesson(client, t_token)

    r = await client.post(
        f"/api/v1/courses/{course_id}/enroll",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.status_code == 201

    r = await client.post(
        f"/api/v1/lessons/{lesson_id}/complete",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.status_code == 200

    # Stat tekshiruvi
    r = await client.get(
        "/api/v1/me/gamification",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.status_code == 200, r.text
    stats = r.json()
    # 5 (lesson) + 100 (course) + 5 (first_lesson badge reward) + 50 (first_course badge reward)
    assert stats["total_points"] >= 105
    assert stats["badges_count"] >= 2
    badge_codes = {b["badge"]["code"] for b in stats["recent_badges"]}
    assert "first_lesson" in badge_codes
    assert "first_course" in badge_codes


async def test_event_is_deduped(client: AsyncClient) -> None:
    t_token = await _login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
    s_token = await _login(client, STUDENT_EMAIL, STUDENT_PASSWORD)
    course_id, lesson_id = await _setup_course_lesson(client, t_token)
    await client.post(
        f"/api/v1/courses/{course_id}/enroll",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    # Bir xil darsni 2 marta complete qilish
    await client.post(
        f"/api/v1/lessons/{lesson_id}/complete",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    await client.post(
        f"/api/v1/lessons/{lesson_id}/complete",
        headers={"Authorization": f"Bearer {s_token}"},
    )

    async with SessionLocal() as db:
        # Faqat 1 ta lesson.completed event bo'lishi kerak (dedupe_key bilan)
        rows = (
            await db.execute(
                select(GamificationEvent).where(
                    GamificationEvent.event_type == "lesson.completed"
                )
            )
        ).scalars().all()
        assert len(rows) == 1


async def test_forum_post_like_awards_author(client: AsyncClient) -> None:
    t_token = await _login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
    s_token = await _login(client, STUDENT_EMAIL, STUDENT_PASSWORD)
    course_id, _ = await _setup_course_lesson(client, t_token)
    await client.post(
        f"/api/v1/courses/{course_id}/enroll",
        headers={"Authorization": f"Bearer {s_token}"},
    )

    # Talaba mavzu va post yaratadi
    r = await client.post(
        "/api/v1/forum/threads",
        json={"course_id": course_id, "title": "Savol"},
        headers={"Authorization": f"Bearer {s_token}"},
    )
    thread_id = r.json()["id"]
    r = await client.post(
        f"/api/v1/forum/threads/{thread_id}/posts",
        json={"body": "Mening javobim"},
        headers={"Authorization": f"Bearer {s_token}"},
    )
    post_id = r.json()["id"]

    # Talabaning stati hozir — base
    r = await client.get(
        "/api/v1/me/gamification",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    points_before = r.json()["total_points"]

    # O'qituvchi like bosadi
    r = await client.post(
        f"/api/v1/forum/posts/{post_id}/like",
        headers={"Authorization": f"Bearer {t_token}"},
    )
    assert r.status_code == 200

    # Talabaga +1 ball (forum.post.liked)
    r = await client.get(
        "/api/v1/me/gamification",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.json()["total_points"] == points_before + 1


async def test_self_like_does_not_award(client: AsyncClient) -> None:
    t_token = await _login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
    s_token = await _login(client, STUDENT_EMAIL, STUDENT_PASSWORD)
    course_id, _ = await _setup_course_lesson(client, t_token)
    await client.post(
        f"/api/v1/courses/{course_id}/enroll",
        headers={"Authorization": f"Bearer {s_token}"},
    )

    r = await client.post(
        "/api/v1/forum/threads",
        json={"course_id": course_id, "title": "Savol"},
        headers={"Authorization": f"Bearer {s_token}"},
    )
    thread_id = r.json()["id"]
    r = await client.post(
        f"/api/v1/forum/threads/{thread_id}/posts",
        json={"body": "javob"},
        headers={"Authorization": f"Bearer {s_token}"},
    )
    post_id = r.json()["id"]

    r = await client.get(
        "/api/v1/me/gamification",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    points_before = r.json()["total_points"]

    # O'zining post'iga like
    r = await client.post(
        f"/api/v1/forum/posts/{post_id}/like",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.status_code == 200

    r = await client.get(
        "/api/v1/me/gamification",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    # O'zining post'iga like ball bermaydi
    assert r.json()["total_points"] == points_before


async def test_leaderboard_returns_active_users(client: AsyncClient) -> None:
    t_token = await _login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
    s_token = await _login(client, STUDENT_EMAIL, STUDENT_PASSWORD)
    course_id, lesson_id = await _setup_course_lesson(client, t_token)
    await client.post(
        f"/api/v1/courses/{course_id}/enroll",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    await client.post(
        f"/api/v1/lessons/{lesson_id}/complete",
        headers={"Authorization": f"Bearer {s_token}"},
    )

    r = await client.get(
        "/api/v1/gamification/leaderboard?scope=total&limit=10",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["scope"] == "total"
    assert len(data["items"]) >= 1
    # Talaba reytingda
    assert data["me_rank"] is not None
    assert data["me_points"] >= 5


async def test_badge_catalog_endpoint(client: AsyncClient) -> None:
    s_token = await _login(client, STUDENT_EMAIL, STUDENT_PASSWORD)
    r = await client.get(
        "/api/v1/gamification/badges",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.status_code == 200
    items = r.json()
    codes = {b["code"] for b in items}
    # Default seed dan hech bo'lmasa shu 4 ta bo'lishi kerak
    assert "first_lesson" in codes
    assert "first_course" in codes
    assert "course_master" in codes
    assert "exam_ace" in codes

"""Phase 13.29 — Talaba E2E smoke testi.

Oqim:
  1. Login student
  2. Kurs yaratish (teacher), modul + dars (teacher)
  3. Talaba kursga yoziladi
  4. Dars tugatadi => course completed
  5. Sertifikat avtomatik berilgan (Phase 11d)
  6. `course.completed` event va `first_course` badge yaratilgan (Phase 11e)
  7. Notification yaratilgan (certificate.issued, badge.awarded)
  8. `/me/gradebook` 1 ta kurs qaytaradi
  9. `/me/gamification` ball va badge ko'rsatadi
  10. `/me/certificates` 1 ta sertifikat
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
from app.modules.notifications.models import Notification
from app.modules.organizations.models import Organization

TEACHER_EMAIL = "teacher@xiuedu.uz"
TEACHER_PASSWORD = "Teacher!2026"
STUDENT_EMAIL = "student@xiuedu.uz"
STUDENT_PASSWORD = "Student!2026"


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def clean_e2e():
    async with SessionLocal() as db:
        # Tartibni saqlab tozalash
        await db.execute(delete(UserBadge))
        await db.execute(delete(UserPoints))
        await db.execute(delete(GamificationEvent))
        await db.execute(delete(Notification))
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
        await seed_badges(db)
        await db.commit()
    yield


async def _login(client: AsyncClient, email: str, password: str) -> str:
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


async def test_student_full_journey(client: AsyncClient) -> None:
    """Phase 13.29 — to'liq talaba oqimi."""
    teacher_token = await _login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
    student_token = await _login(client, STUDENT_EMAIL, STUDENT_PASSWORD)
    t_h = {"Authorization": f"Bearer {teacher_token}"}
    s_h = {"Authorization": f"Bearer {student_token}"}

    # 1. Teacher kurs + modul + dars
    r = await client.post(
        "/api/v1/courses",
        json={
            "title": "E2E sinov kursi",
            "slug": f"e2e-{uuid.uuid4().hex[:8]}",
            "type": "open",
            "language": "uz-lat",
            "enrollment_type": "self",
        },
        headers=t_h,
    )
    course_id = r.json()["id"]
    r = await client.post(
        f"/api/v1/courses/{course_id}/modules", json={"title": "M1"}, headers=t_h
    )
    module_id = r.json()["id"]
    r = await client.post(
        f"/api/v1/modules/{module_id}/lessons",
        json={"title": "Yagona dars"},
        headers=t_h,
    )
    lesson_id = r.json()["id"]
    await client.post(f"/api/v1/courses/{course_id}/publish", headers=t_h)

    # 2. Student enroll
    r = await client.post(f"/api/v1/courses/{course_id}/enroll", headers=s_h)
    assert r.status_code == 201

    # 3. Dars tugatish => kurs 100% => sertifikat + badge + notification triggerlari
    r = await client.post(f"/api/v1/lessons/{lesson_id}/complete", headers=s_h)
    assert r.status_code == 200

    # 4. /me/gradebook bitta kurs (hech gradedlangan exam yo'q, lekin kurs ro'yxatda)
    r = await client.get("/api/v1/me/gradebook", headers=s_h)
    assert r.status_code == 200
    gb = r.json()
    assert len(gb) == 1
    assert gb[0]["course_id"] == course_id

    # 5. /me/gamification — ball va badge
    r = await client.get("/api/v1/me/gamification", headers=s_h)
    assert r.status_code == 200
    stats = r.json()
    # 5 (lesson) + 100 (course) + first_lesson reward + first_course reward
    assert stats["total_points"] > 100
    assert stats["badges_count"] >= 2
    codes = {b["badge"]["code"] for b in stats["recent_badges"]}
    assert "first_course" in codes

    # 6. /me/certificates — 1 ta sertifikat
    r = await client.get("/api/v1/me/certificates", headers=s_h)
    assert r.status_code == 200
    certs = r.json()
    assert len(certs) == 1
    assert certs[0]["certificate_number"].startswith("XIU-")

    # 7. Public verify
    code = certs[0]["verification_url"].rsplit("/", 1)[-1]
    r = await client.get(f"/api/v1/verify/{code}")
    assert r.status_code == 200
    assert r.json()["valid"] is True

    # 8. Notifications: certificate.issued + badge.awarded yaratilgan
    r = await client.get(
        "/api/v1/notifications?unread_only=true&page_size=50", headers=s_h
    )
    assert r.status_code == 200
    types = [n["event_type"] for n in r.json()["items"]]
    assert "certificate.issued" in types
    assert "badge.awarded" in types

    # 9. /me/conversations — boshlang'ich bo'sh
    r = await client.get("/api/v1/chat/conversations", headers=s_h)
    assert r.status_code == 200
    assert r.json()["total"] == 0

    # 10. Forum thread yaratish (talaba kurs a'zosi)
    r = await client.post(
        "/api/v1/forum/threads",
        json={"course_id": course_id, "title": "Sinov mavzu"},
        headers=s_h,
    )
    assert r.status_code == 201
    assert r.json()["author_name"]  # Phase 13.22

    # 11. Lesson comment yaratish — author_name resolved
    r = await client.post(
        f"/api/v1/lessons/{lesson_id}/comments",
        json={"body": "Yaxshi dars"},
        headers=s_h,
    )
    assert r.status_code == 201
    assert r.json()["author_name"]  # Phase 13.16

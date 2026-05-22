"""Phase 11b — Communications smoke testlari.

Coverage:
  - Direct chat ochish (idempotent — get_or_create)
  - Xabar yuborish + listMessages
  - Mark read => unread_count 0
  - Forum thread + post + like toggle
  - Locked thread'ga javob => 403
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
    Conversation,
    ConversationMember,
    ForumPost,
    ForumPostLike,
    ForumThread,
    Message,
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
async def clean_communications():
    async with SessionLocal() as db:
        await db.execute(delete(ForumPostLike))
        await db.execute(delete(ForumPost))
        await db.execute(delete(ForumThread))
        await db.execute(delete(Message))
        await db.execute(delete(ConversationMember))
        await db.execute(delete(Conversation))
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


async def _teacher(client: AsyncClient) -> tuple[str, int]:
    token = await _login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
    r = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    return token, r.json()["id"]


async def _student(client: AsyncClient) -> tuple[str, int]:
    token = await _login(client, STUDENT_EMAIL, STUDENT_PASSWORD)
    r = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    return token, r.json()["id"]


async def _new_student(client: AsyncClient) -> tuple[str, int]:
    email = _email()
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD, "full_name": "Test Talaba"},
    )
    user_id = r.json()["id"]
    token = await _login(client, email, VALID_PASSWORD)
    return token, user_id


async def _create_published_course(
    client: AsyncClient, teacher_token: str
) -> int:
    body = {
        "title": "Forum sinov kursi",
        "slug": _slug(),
        "description": "Forum smoke test uchun kurs",
        "type": "open",
        "language": "uz-lat",
        "enrollment_type": "self",
    }
    r = await client.post(
        "/api/v1/courses",
        json=body,
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert r.status_code == 201, r.text
    course_id = r.json()["id"]
    r = await client.post(
        f"/api/v1/courses/{course_id}/publish",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert r.status_code == 200, r.text
    return course_id


# ----------------------------------------------------------------------------
# CHAT
# ----------------------------------------------------------------------------


async def test_direct_chat_idempotent(client: AsyncClient) -> None:
    t_token, t_id = await _teacher(client)
    s_token, s_id = await _student(client)

    r1 = await client.post(
        "/api/v1/chat/conversations/direct",
        json={"peer_user_id": s_id},
        headers={"Authorization": f"Bearer {t_token}"},
    )
    assert r1.status_code == 201, r1.text
    conv1 = r1.json()
    assert conv1["type"] == "direct"
    assert set(conv1["member_ids"]) == {t_id, s_id}

    # Ikkinchi marta — eski chatni qaytaradi (yangi yaratmaydi)
    r2 = await client.post(
        "/api/v1/chat/conversations/direct",
        json={"peer_user_id": t_id},
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r2.status_code == 201, r2.text
    assert r2.json()["id"] == conv1["id"]


async def test_send_message_and_unread(client: AsyncClient) -> None:
    t_token, _ = await _teacher(client)
    s_token, s_id = await _student(client)

    r = await client.post(
        "/api/v1/chat/conversations/direct",
        json={"peer_user_id": s_id},
        headers={"Authorization": f"Bearer {t_token}"},
    )
    conv_id = r.json()["id"]

    # O'qituvchi yuboradi
    r = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        json={"body": "Salom talaba"},
        headers={"Authorization": f"Bearer {t_token}"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["body"] == "Salom talaba"

    # Talabada 1 ta unread
    r = await client.get(
        "/api/v1/chat/conversations",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.status_code == 200
    items = r.json()["items"]
    my = next(c for c in items if c["id"] == conv_id)
    assert my["unread_count"] == 1
    assert my["last_message_preview"] == "Salom talaba"

    # Talaba thread'ni o'qiydi va read belgilaydi
    r = await client.get(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1

    r = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/read",
        json={"last_message_id": None},
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.status_code == 200
    assert r.json()["unread_count"] == 0


async def test_non_member_cannot_send(client: AsyncClient) -> None:
    t_token, _ = await _teacher(client)
    _, s_id = await _student(client)
    other_token, _ = await _new_student(client)

    r = await client.post(
        "/api/v1/chat/conversations/direct",
        json={"peer_user_id": s_id},
        headers={"Authorization": f"Bearer {t_token}"},
    )
    conv_id = r.json()["id"]

    r = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        json={"body": "intruder"},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert r.status_code == 403


# ----------------------------------------------------------------------------
# FORUM
# ----------------------------------------------------------------------------


async def test_forum_thread_and_reply(client: AsyncClient) -> None:
    t_token, _ = await _teacher(client)
    s_token, _ = await _student(client)
    course_id = await _create_published_course(client, t_token)

    # Talaba kursga yoziladi
    r = await client.post(
        f"/api/v1/courses/{course_id}/enroll",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.status_code == 201, r.text

    # Talaba mavzu yaratadi
    r = await client.post(
        "/api/v1/forum/threads",
        json={
            "course_id": course_id,
            "title": "Algoritm haqida savol",
            "body": "Binary search murakkabligi qancha?",
        },
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.status_code == 201, r.text
    thread = r.json()
    assert not thread["is_announcement"]
    thread_id = thread["id"]

    # O'qituvchi javob yozadi
    r = await client.post(
        f"/api/v1/forum/threads/{thread_id}/posts",
        json={"body": "O(log n)"},
        headers={"Authorization": f"Bearer {t_token}"},
    )
    assert r.status_code == 201, r.text
    post_id = r.json()["id"]

    # Talaba post'ga like qo'yadi
    r = await client.post(
        f"/api/v1/forum/posts/{post_id}/like",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.status_code == 200
    assert r.json()["like_count"] == 1
    assert r.json()["liked_by_me"] is True

    # Yana bosish — like olib tashlanadi
    r = await client.post(
        f"/api/v1/forum/posts/{post_id}/like",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.status_code == 200
    assert r.json()["like_count"] == 0
    assert r.json()["liked_by_me"] is False


async def test_student_cannot_create_announcement(client: AsyncClient) -> None:
    t_token, _ = await _teacher(client)
    s_token, _ = await _student(client)
    course_id = await _create_published_course(client, t_token)
    r = await client.post(
        f"/api/v1/courses/{course_id}/enroll",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.status_code == 201

    r = await client.post(
        "/api/v1/forum/threads",
        json={
            "course_id": course_id,
            "title": "Spam announcement",
            "is_announcement": True,
        },
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.status_code == 403


async def test_locked_thread_blocks_reply(client: AsyncClient) -> None:
    t_token, _ = await _teacher(client)
    s_token, _ = await _student(client)
    course_id = await _create_published_course(client, t_token)
    await client.post(
        f"/api/v1/courses/{course_id}/enroll",
        headers={"Authorization": f"Bearer {s_token}"},
    )

    # O'qituvchi mavzu yaratadi va yopadi
    r = await client.post(
        "/api/v1/forum/threads",
        json={"course_id": course_id, "title": "Locked tema"},
        headers={"Authorization": f"Bearer {t_token}"},
    )
    thread_id = r.json()["id"]
    r = await client.patch(
        f"/api/v1/forum/threads/{thread_id}",
        json={"is_locked": True},
        headers={"Authorization": f"Bearer {t_token}"},
    )
    assert r.status_code == 200
    assert r.json()["is_locked"] is True

    # Talaba javob bera olmaydi
    r = await client.post(
        f"/api/v1/forum/threads/{thread_id}/posts",
        json={"body": "javob"},
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert r.status_code == 403


async def test_non_enrolled_cannot_access_forum(client: AsyncClient) -> None:
    t_token, _ = await _teacher(client)
    other_token, _ = await _new_student(client)
    course_id = await _create_published_course(client, t_token)

    r = await client.get(
        f"/api/v1/forum/courses/{course_id}/threads",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert r.status_code == 403

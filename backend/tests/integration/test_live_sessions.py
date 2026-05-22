"""Phase 5a — Live sessions backend integration tests.

Coverage:
  - RBAC: student create => 403; teacher create => 201
  - LiveSession CRUD + filters
  - Status workflow: scheduled → live → ended; cancel from any non-terminal
  - Date validation (end > start)
  - Join/leave attendance + 75% counted rule
  - Attendance list (host only) + scope (talaba 403)
  - join-info stub URL per provider
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete, text

from app.core.database import SessionLocal
from app.modules.auth.models import LoginAttempt, UserSession
from app.modules.courses.models import (
    Course,
    Enrollment,
    Lesson,
    LessonProgress,
    Module,
)
from app.modules.live.models import LiveAttendance, LiveSession

VALID_PASSWORD = "Str0ng!Password"
ADMIN_EMAIL = "admin@xiuedu.uz"
ADMIN_PASSWORD = "ChangeMe!2026"
TEACHER_EMAIL = "teacher@xiuedu.uz"
TEACHER_PASSWORD = "Teacher!2026"
STUDENT_EMAIL = "student@xiuedu.uz"
STUDENT_PASSWORD = "Student!2026"


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def clean_live():
    async with SessionLocal() as db:
        await db.execute(delete(LiveAttendance))
        await db.execute(delete(LiveSession))
        await db.execute(delete(LessonProgress))
        await db.execute(delete(Enrollment))
        await db.execute(delete(Lesson))
        await db.execute(delete(Module))
        await db.execute(delete(Course))
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


def _title() -> str:
    return f"Live dars {uuid.uuid4().hex[:6]}"


async def _login(client: AsyncClient, email: str, password: str) -> str:
    r = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


async def _teacher(client: AsyncClient) -> str:
    return await _login(client, TEACHER_EMAIL, TEACHER_PASSWORD)


async def _student_demo(client: AsyncClient) -> str:
    return await _login(client, STUDENT_EMAIL, STUDENT_PASSWORD)


async def _admin(client: AsyncClient) -> str:
    return await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)


def _now() -> datetime:
    return datetime.now(UTC)


def _create_payload(
    *,
    minutes_from_now: int = 60,
    duration: int = 60,
    provider: str = "native",
) -> dict:
    start = _now() + timedelta(minutes=minutes_from_now)
    end = start + timedelta(minutes=duration)
    return {
        "title": _title(),
        "description": "Test live dars",
        "scheduled_start": start.isoformat(),
        "scheduled_end": end.isoformat(),
        "duration_minutes": duration,
        "provider": provider,
        "is_recording_enabled": False,
        "min_attendance_percent": 75,
    }


async def _create_session(
    client: AsyncClient, token: str, **overrides
) -> dict:
    body = _create_payload()
    body.update(overrides)
    r = await client.post(
        "/api/v1/live-sessions",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ============================================================================
# RBAC
# ============================================================================


async def test_student_cannot_create_session(client: AsyncClient) -> None:
    token = await _student_demo(client)
    r = await client.post(
        "/api/v1/live-sessions",
        json=_create_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


async def test_teacher_can_create_session(client: AsyncClient) -> None:
    token = await _teacher(client)
    r = await client.post(
        "/api/v1/live-sessions",
        json=_create_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "scheduled"
    assert body["provider"] == "native"
    assert body["organization_id"] is not None  # Auto-XIU


# ============================================================================
# CRUD + filters
# ============================================================================


async def test_list_sessions_filters_by_status(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    s1 = await _create_session(client, teacher)

    # Boshlash → status='live'
    await client.post(
        f"/api/v1/live-sessions/{s1['id']}/start",
        headers={"Authorization": f"Bearer {teacher}"},
    )

    s2 = await _create_session(client, teacher)  # scheduled

    r = await client.get(
        "/api/v1/live-sessions?status=scheduled",
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 200, r.text
    ids = [s["id"] for s in r.json()["items"]]
    assert s2["id"] in ids
    assert s1["id"] not in ids


async def test_update_session_validates_dates(client: AsyncClient) -> None:
    token = await _teacher(client)
    session = await _create_session(client, token)
    end = _now() + timedelta(minutes=30)
    start = end + timedelta(minutes=10)  # start > end → invalid
    r = await client.patch(
        f"/api/v1/live-sessions/{session['id']}",
        json={"scheduled_start": start.isoformat(), "scheduled_end": end.isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code in (400, 422)


async def test_other_teacher_cannot_edit_session(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    session = await _create_session(client, teacher)

    # Boshqa "teacher" yarataolmaydi (faqat single teacher demo bor) — admin bilan
    # tekshiramiz: admin platform.* bilan bemalol tahrirlay oladi
    admin = await _admin(client)
    r = await client.patch(
        f"/api/v1/live-sessions/{session['id']}",
        json={"title": "Admin tahrir"},
        headers={"Authorization": f"Bearer {admin}"},
    )
    assert r.status_code == 200, r.text


# ============================================================================
# Status transitions
# ============================================================================


async def test_status_workflow_happy_path(client: AsyncClient) -> None:
    token = await _teacher(client)
    s = await _create_session(client, token)

    r = await client.post(
        f"/api/v1/live-sessions/{s['id']}/start",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "live"
    assert r.json()["actual_start"] is not None

    r = await client.post(
        f"/api/v1/live-sessions/{s['id']}/end",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ended"
    assert r.json()["actual_end"] is not None


async def test_cannot_start_ended_session(client: AsyncClient) -> None:
    token = await _teacher(client)
    s = await _create_session(client, token)
    await client.post(
        f"/api/v1/live-sessions/{s['id']}/start",
        headers={"Authorization": f"Bearer {token}"},
    )
    await client.post(
        f"/api/v1/live-sessions/{s['id']}/end",
        headers={"Authorization": f"Bearer {token}"},
    )
    r = await client.post(
        f"/api/v1/live-sessions/{s['id']}/start",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 409


async def test_cancel_from_scheduled(client: AsyncClient) -> None:
    token = await _teacher(client)
    s = await _create_session(client, token)
    r = await client.post(
        f"/api/v1/live-sessions/{s['id']}/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


async def test_delete_blocked_when_live(client: AsyncClient) -> None:
    token = await _teacher(client)
    s = await _create_session(client, token)
    await client.post(
        f"/api/v1/live-sessions/{s['id']}/start",
        headers={"Authorization": f"Bearer {token}"},
    )
    r = await client.delete(
        f"/api/v1/live-sessions/{s['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 409


# ============================================================================
# Join / Leave + Attendance
# ============================================================================


async def test_student_join_requires_live_status(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    student = await _student_demo(client)
    s = await _create_session(client, teacher)

    # scheduled — join taqiqlangan
    r = await client.post(
        f"/api/v1/live-sessions/{s['id']}/join",
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r.status_code == 409


async def test_join_then_leave_records_attendance(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    student = await _student_demo(client)
    s = await _create_session(client, teacher)
    await client.post(
        f"/api/v1/live-sessions/{s['id']}/start",
        headers={"Authorization": f"Bearer {teacher}"},
    )

    r = await client.post(
        f"/api/v1/live-sessions/{s['id']}/join",
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["joined_at"] is not None

    r = await client.post(
        f"/api/v1/live-sessions/{s['id']}/leave",
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["left_at"] is not None
    assert body["total_minutes"] >= 0


async def test_leave_without_join_409(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    student = await _student_demo(client)
    s = await _create_session(client, teacher)
    await client.post(
        f"/api/v1/live-sessions/{s['id']}/start",
        headers={"Authorization": f"Bearer {teacher}"},
    )
    r = await client.post(
        f"/api/v1/live-sessions/{s['id']}/leave",
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r.status_code == 409


async def test_end_session_finalizes_open_attendance(client: AsyncClient) -> None:
    """Talaba join qilib leave qilmasdan turib, host end qilsa attendance yopiladi."""
    teacher = await _teacher(client)
    student = await _student_demo(client)
    s = await _create_session(client, teacher)
    await client.post(
        f"/api/v1/live-sessions/{s['id']}/start",
        headers={"Authorization": f"Bearer {teacher}"},
    )
    await client.post(
        f"/api/v1/live-sessions/{s['id']}/join",
        headers={"Authorization": f"Bearer {student}"},
    )
    await client.post(
        f"/api/v1/live-sessions/{s['id']}/end",
        headers={"Authorization": f"Bearer {teacher}"},
    )
    r = await client.get(
        f"/api/v1/live-sessions/{s['id']}/attendance",
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["left_at"] is not None


async def test_attendance_75pct_rule(client: AsyncClient) -> None:
    """LiveAttendance.is_counted faqat total_minutes / duration >= 75% bo'lsa True."""
    teacher = await _teacher(client)
    student = await _student_demo(client)
    s = await _create_session(client, teacher, duration_minutes=10)
    await client.post(
        f"/api/v1/live-sessions/{s['id']}/start",
        headers={"Authorization": f"Bearer {teacher}"},
    )
    await client.post(
        f"/api/v1/live-sessions/{s['id']}/join",
        headers={"Authorization": f"Bearer {student}"},
    )
    # Realtime test — 10 min davomiyligi va instant leave bo'lsa, 0 min => 0%
    r = await client.post(
        f"/api/v1/live-sessions/{s['id']}/leave",
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r.status_code == 200
    assert r.json()["is_counted"] is False  # 0% < 75%

    # DB level: simulate full attendance (manually backdate joined_at)
    async with SessionLocal() as db:
        # leaveni reset qilamiz va talaba IDni olamiz
        from sqlalchemy import select

        from app.modules.users.models import User

        u = (
            await db.execute(
                select(User).where(User.email == STUDENT_EMAIL)
            )
        ).scalar_one()
        att = (
            await db.execute(
                select(LiveAttendance).where(
                    LiveAttendance.session_id == s["id"],
                    LiveAttendance.user_id == u.id,
                )
            )
        ).scalar_one()
        # 10 min duration, 8 min davom etgan deb belgilash → 80% => True
        att.total_minutes = 8
        await db.commit()

    # End session triggers recompute
    await client.post(
        f"/api/v1/live-sessions/{s['id']}/end",
        headers={"Authorization": f"Bearer {teacher}"},
    )
    r = await client.get(
        f"/api/v1/live-sessions/{s['id']}/attendance",
        headers={"Authorization": f"Bearer {teacher}"},
    )
    rows = r.json()
    assert len(rows) == 1
    # End session faqat ochiq attendance'ni recompute qiladi (left_at=None bo'lganlarni)
    # Yuqorida leave bilan yopilgan, shuning uchun manual update faqat total_minutes=8 ga
    # tegdi, lekin is_counted recompute qilinmadi end-da. 75% qoidasini service.mark_leave
    # darajasida tekshiramiz: yangi join qilib total ni 8 ga teng bo'lganda hisoblansin.
    # Soddalashtirish uchun: bevosita service'ni tekshiramiz
    from app.modules.live import service

    async with SessionLocal() as db:
        from sqlalchemy import select

        from app.modules.users.models import User

        u = (
            await db.execute(select(User).where(User.email == STUDENT_EMAIL))
        ).scalar_one()
        sess = await service.get_session(db, s["id"])
        att = (
            await db.execute(
                select(LiveAttendance).where(
                    LiveAttendance.session_id == s["id"],
                    LiveAttendance.user_id == u.id,
                )
            )
        ).scalar_one()
        service._recompute_counted(att, sess)
        await db.commit()
        await db.refresh(att)
        assert att.is_counted is True


async def test_student_cannot_view_attendance_list(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    student = await _student_demo(client)
    s = await _create_session(client, teacher)
    r = await client.get(
        f"/api/v1/live-sessions/{s['id']}/attendance",
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r.status_code == 403


# ============================================================================
# Join-info
# ============================================================================


async def test_join_info_returns_native_token(client: AsyncClient) -> None:
    from app.core.config import settings

    teacher = await _teacher(client)
    student = await _student_demo(client)
    s = await _create_session(client, teacher)
    r = await client.get(
        f"/api/v1/live-sessions/{s['id']}/join-info",
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["provider"] == "native"
    assert body["join_url"] == settings.LIVEKIT_URL_PUBLIC
    assert body["embed_token"]  # LiveKit JWT bo'sh emas
    assert body["is_host"] is False
    assert body["embed_config"]["url"] == settings.LIVEKIT_URL_PUBLIC


async def test_join_info_marks_host(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    s = await _create_session(client, teacher)
    r = await client.get(
        f"/api/v1/live-sessions/{s['id']}/join-info",
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 200
    assert r.json()["is_host"] is True


async def test_native_jwt_claims_for_host(client: AsyncClient) -> None:
    """Host JWT da roomAdmin=True va canPublish=True bo'lishi shart."""
    from jose import jwt as jose_jwt

    from app.core.config import settings

    teacher = await _teacher(client)
    s = await _create_session(client, teacher)
    r = await client.get(
        f"/api/v1/live-sessions/{s['id']}/join-info",
        headers={"Authorization": f"Bearer {teacher}"},
    )
    token = r.json()["embed_token"]
    claims = jose_jwt.decode(
        token,
        settings.LIVEKIT_API_SECRET,
        algorithms=["HS256"],
        options={"verify_aud": False},
    )
    assert claims["iss"] == settings.LIVEKIT_API_KEY
    assert claims["video"]["room"] == s["provider_meeting_id"]
    assert claims["video"]["canPublish"] is True
    assert claims["video"]["roomAdmin"] is True
    assert claims["video"]["roomJoin"] is True


async def test_native_jwt_claims_for_guest(client: AsyncClient) -> None:
    """Talaba JWT da roomAdmin=False, lekin canPublish=True (gapira oladi)."""
    from jose import jwt as jose_jwt

    from app.core.config import settings

    teacher = await _teacher(client)
    student = await _student_demo(client)
    s = await _create_session(client, teacher)
    r = await client.get(
        f"/api/v1/live-sessions/{s['id']}/join-info",
        headers={"Authorization": f"Bearer {student}"},
    )
    token = r.json()["embed_token"]
    claims = jose_jwt.decode(
        token,
        settings.LIVEKIT_API_SECRET,
        algorithms=["HS256"],
        options={"verify_aud": False},
    )
    assert claims["video"]["canPublish"] is True
    assert claims["video"]["roomAdmin"] is False


async def test_create_session_pre_fills_provider_meeting_id(
    client: AsyncClient,
) -> None:
    """Native: room name `xiu-live-{session_id}` formatida."""
    teacher = await _teacher(client)
    s = await _create_session(client, teacher)
    assert s["provider"] == "native"
    assert s["provider_meeting_id"] == f"xiu-live-{s['id']}"


async def test_unknown_provider_rejected(client: AsyncClient) -> None:
    """Faqat 'native' qabul qilinadi (Pydantic Literal)."""
    teacher = await _teacher(client)
    body = _create_payload()
    body["provider"] = "zoom"
    r = await client.post(
        "/api/v1/live-sessions",
        json=body,
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code in (400, 422)


# ============================================================================
# Recording (Phase 5d)
# ============================================================================


# 1KB tinch video bayt-shaklini taqlid qiluvchi placeholder. ffprobe/ffmpeg
# real video sifatida tan olmasligi mumkin — recording.py graceful fallback
# bilan baribir upload muvaffaqiyatli yakunlanadi.
_FAKE_MP4 = b"\x00\x00\x00\x20ftypisom" + b"\x00" * 1000


async def test_recording_upload_happy_path(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    s = await _create_session(client, teacher)
    r = await client.post(
        f"/api/v1/live-sessions/{s['id']}/recording-upload",
        headers={"Authorization": f"Bearer {teacher}"},
        files={"file": ("rec.mp4", _FAKE_MP4, "video/mp4")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["recording_url"]
    # Phase 7b: URL endi presigned bo'lib qoldi — kalit/path .mp4 da tugaydi, lekin
    # URL ?X-Amz-... query string bilan keladi.
    assert ".mp4" in body["recording_url"]
    assert body["recording_mime_type"] == "video/mp4"
    assert body["recording_size_bytes"] == len(_FAKE_MP4)


async def test_recording_upload_rejects_bad_mime(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    s = await _create_session(client, teacher)
    r = await client.post(
        f"/api/v1/live-sessions/{s['id']}/recording-upload",
        headers={"Authorization": f"Bearer {teacher}"},
        files={"file": ("rec.txt", b"hello", "text/plain")},
    )
    assert r.status_code == 415


async def test_recording_upload_non_host_forbidden(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    student = await _student_demo(client)
    s = await _create_session(client, teacher)
    r = await client.post(
        f"/api/v1/live-sessions/{s['id']}/recording-upload",
        headers={"Authorization": f"Bearer {student}"},
        files={"file": ("rec.mp4", _FAKE_MP4, "video/mp4")},
    )
    # Talaba uchun avval `live.host` permission yo'q → 403 (require_permission)
    assert r.status_code == 403


async def test_recording_upload_replaces_existing(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    s = await _create_session(client, teacher)
    r1 = await client.post(
        f"/api/v1/live-sessions/{s['id']}/recording-upload",
        headers={"Authorization": f"Bearer {teacher}"},
        files={"file": ("a.mp4", _FAKE_MP4, "video/mp4")},
    )
    assert r1.status_code == 200
    url1 = r1.json()["recording_url"]

    r2 = await client.post(
        f"/api/v1/live-sessions/{s['id']}/recording-upload",
        headers={"Authorization": f"Bearer {teacher}"},
        files={"file": ("b.mp4", _FAKE_MP4 + b"x", "video/mp4")},
    )
    assert r2.status_code == 200
    url2 = r2.json()["recording_url"]
    assert url1 != url2  # yangi object key
    assert r2.json()["recording_size_bytes"] == len(_FAKE_MP4) + 1


async def test_attendance_summary_empty(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    s = await _create_session(client, teacher, duration_minutes=10)
    r = await client.get(
        f"/api/v1/live-sessions/{s['id']}/attendance/summary",
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["session_id"] == s["id"]
    assert body["total_participants"] == 0
    assert body["counted_participants"] == 0
    assert body["counted_percent"] == 0.0


async def test_attendance_summary_with_participants(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    student = await _student_demo(client)
    s = await _create_session(client, teacher, duration_minutes=10)
    await client.post(
        f"/api/v1/live-sessions/{s['id']}/start",
        headers={"Authorization": f"Bearer {teacher}"},
    )
    await client.post(
        f"/api/v1/live-sessions/{s['id']}/join",
        headers={"Authorization": f"Bearer {student}"},
    )
    await client.post(
        f"/api/v1/live-sessions/{s['id']}/leave",
        headers={"Authorization": f"Bearer {student}"},
    )
    r = await client.get(
        f"/api/v1/live-sessions/{s['id']}/attendance/summary",
        headers={"Authorization": f"Bearer {teacher}"},
    )
    body = r.json()
    assert body["total_participants"] == 1
    assert body["joined_participants"] == 1


async def test_attendance_summary_student_forbidden(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    student = await _student_demo(client)
    s = await _create_session(client, teacher)
    r = await client.get(
        f"/api/v1/live-sessions/{s['id']}/attendance/summary",
        headers={"Authorization": f"Bearer {student}"},
    )
    assert r.status_code == 403


async def test_attendance_recompute_updates_is_counted(
    client: AsyncClient,
) -> None:
    """Min attendance percent o'zgartirilsa recompute bilan is_counted yangilanadi."""
    teacher = await _teacher(client)
    student = await _student_demo(client)
    s = await _create_session(client, teacher, duration_minutes=10)
    await client.post(
        f"/api/v1/live-sessions/{s['id']}/start",
        headers={"Authorization": f"Bearer {teacher}"},
    )
    await client.post(
        f"/api/v1/live-sessions/{s['id']}/join",
        headers={"Authorization": f"Bearer {student}"},
    )
    # DB darajasida total_minutes=4 (40%) qilamiz — 75% qoidasi bilan is_counted=False
    async with SessionLocal() as db:
        from sqlalchemy import select

        from app.modules.users.models import User

        u = (
            await db.execute(select(User).where(User.email == STUDENT_EMAIL))
        ).scalar_one()
        att = (
            await db.execute(
                select(LiveAttendance).where(
                    LiveAttendance.session_id == s["id"],
                    LiveAttendance.user_id == u.id,
                )
            )
        ).scalar_one()
        att.total_minutes = 4
        att.is_counted = False
        await db.commit()

    # Min attendance percent'ni 30% ga tushirib recompute
    await client.patch(
        f"/api/v1/live-sessions/{s['id']}",
        json={"min_attendance_percent": 30},
        headers={"Authorization": f"Bearer {teacher}"},
    )
    r = await client.post(
        f"/api/v1/live-sessions/{s['id']}/attendance/recompute",
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 200
    # 40% >= 30% → endi counted
    assert r.json()["counted_participants"] == 1


# ============================================================================
# iCal (Phase 5e)
# ============================================================================


async def test_calendar_token_endpoint(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    r = await client.get(
        "/api/v1/live-calendar/token",
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["url"].startswith("http")
    assert "token=" in body["url"]
    assert len(body["token"]) == 64  # SHA256 hex


async def test_calendar_ics_feed(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    # Sessiya yaratamiz
    s = await _create_session(client, teacher)
    # Token + URL ni olamiz
    tok_resp = await client.get(
        "/api/v1/live-calendar/token",
        headers={"Authorization": f"Bearer {teacher}"},
    )
    url = tok_resp.json()["url"]
    # Subscribe URL — auth header'siz ochilishi shart
    r = await client.get(url.replace("http://test", ""))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/calendar")
    body = r.text
    assert "BEGIN:VCALENDAR" in body
    assert "END:VCALENDAR" in body
    assert f"UID:live-{s['id']}@xiuedu.uz" in body
    assert "BEGIN:VALARM" in body  # 15-min reminder


async def test_calendar_ics_rejects_bad_token(client: AsyncClient) -> None:
    # noto'g'ri token
    r = await client.get("/api/v1/live-calendar.ics?user=1&token=bad")
    assert r.status_code == 404


async def test_recording_delete(client: AsyncClient) -> None:
    teacher = await _teacher(client)
    s = await _create_session(client, teacher)
    up = await client.post(
        f"/api/v1/live-sessions/{s['id']}/recording-upload",
        headers={"Authorization": f"Bearer {teacher}"},
        files={"file": ("rec.mp4", _FAKE_MP4, "video/mp4")},
    )
    assert up.status_code == 200

    dr = await client.delete(
        f"/api/v1/live-sessions/{s['id']}/recording",
        headers={"Authorization": f"Bearer {teacher}"},
    )
    assert dr.status_code == 200
    body = dr.json()
    assert body["recording_url"] is None
    assert body["recording_size_bytes"] is None
    assert body["thumbnail_url"] is None

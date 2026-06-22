"""Live darslar service (Phase 5a).

Asosiy biznes-mantiq:
- LiveSession CRUD (status workflow: scheduled → live → ended; har vaqt → cancelled)
- start/end — pedagog yoki host_user_id boshlaydi/tugatadi
- Join/leave — talabaning attendance yozuvi avtomatik yaratiladi/yangilanadi
- Davomat (5e da to'liq qilinadi) — hozir min_attendance_percent qoidasi 75%
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.tenant import get_xiu_org_id
from app.modules.courses.models import Course, Lesson
from app.modules.live.models import LiveAdmission, LiveAttendance, LiveSession
from app.modules.live.providers import ProviderUser, get_provider
from app.modules.live.schemas import (
    LiveSessionCreateRequest,
    LiveSessionUpdateRequest,
)
from app.modules.users.models import User


def _now() -> datetime:
    return datetime.now(UTC)


# Status transitions:
#   scheduled → live | cancelled
#   live      → ended | cancelled
#   ended     → (terminal)
#   cancelled → (terminal)
LIVE_TRANSITIONS: dict[str, set[str]] = {
    "scheduled": {"live", "cancelled"},
    "live": {"ended", "cancelled"},
    "ended": set(),
    "cancelled": set(),
}


# ============================================================================
# CRUD
# ============================================================================


async def list_sessions(
    db: AsyncSession,
    *,
    status_: str | None = None,
    course_id: int | None = None,
    lesson_id: int | None = None,
    host_user_id: int | None = None,
    starts_after: datetime | None = None,
    starts_before: datetime | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[LiveSession], int]:
    stmt = select(LiveSession)
    if status_ is not None:
        stmt = stmt.where(LiveSession.status == status_)
    if course_id is not None:
        stmt = stmt.where(LiveSession.course_id == course_id)
    if lesson_id is not None:
        stmt = stmt.where(LiveSession.lesson_id == lesson_id)
    if host_user_id is not None:
        stmt = stmt.where(LiveSession.host_user_id == host_user_id)
    if starts_after is not None:
        stmt = stmt.where(LiveSession.scheduled_start >= starts_after)
    if starts_before is not None:
        stmt = stmt.where(LiveSession.scheduled_start <= starts_before)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(LiveSession.title).like(like),
                func.lower(LiveSession.description).like(like),
            )
        )

    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    stmt = (
        stmt.order_by(desc(LiveSession.scheduled_start))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, int(total)


async def get_session(db: AsyncSession, session_id: int) -> LiveSession:
    stmt = select(LiveSession).where(LiveSession.id == session_id)
    s = (await db.execute(stmt)).scalar_one_or_none()
    if s is None:
        raise NotFoundError("Live session topilmadi")
    return s


async def _validate_course_lesson(
    db: AsyncSession, course_id: int | None, lesson_id: int | None
) -> None:
    """Course/lesson FK lar haqiqiy ekanligini tekshirish."""
    if course_id is not None:
        c = (
            await db.execute(select(Course).where(Course.id == course_id))
        ).scalar_one_or_none()
        if c is None:
            raise ValidationError("Course topilmadi")
    if lesson_id is not None:
        le = (
            await db.execute(select(Lesson).where(Lesson.id == lesson_id))
        ).scalar_one_or_none()
        if le is None:
            raise ValidationError("Lesson topilmadi")


async def create_session(
    db: AsyncSession, data: LiveSessionCreateRequest, *, host_user_id: int
) -> LiveSession:
    payload = data.model_dump()
    if payload.get("organization_id") is None:
        payload["organization_id"] = await get_xiu_org_id(db)
    await _validate_course_lesson(db, payload.get("course_id"), payload.get("lesson_id"))

    session = LiveSession(host_user_id=host_user_id, **payload)
    db.add(session)
    await db.flush()  # id ni olish uchun

    # Provider'ga moslab room name'ni avtomatik to'ldiramiz
    provider = get_provider(session.provider)
    session.provider_meeting_id = provider.make_room_name(session.id)

    await db.flush()
    await db.refresh(session)

    # Phase 7d — yozilgan talabalarga bildirishnoma
    if session.course_id:
        try:
            from app.modules.notifications.service import notify_live_scheduled
            await notify_live_scheduled(
                db,
                session_id=session.id,
                title=session.title,
                scheduled_start=session.scheduled_start.isoformat(),
                course_id=session.course_id,
            )
        except Exception:  # noqa: BLE001
            import logging
            logging.getLogger(__name__).exception(
                "notify_live_scheduled.failed session=%s", session.id
            )
    return session


async def update_session(
    db: AsyncSession, session_id: int, data: LiveSessionUpdateRequest
) -> LiveSession:
    session = await get_session(db, session_id)
    if session.status in ("ended", "cancelled"):
        raise ConflictError("Tugagan yoki bekor qilingan sessionni tahrirlab bo'lmaydi")

    payload = data.model_dump(exclude_unset=True)
    await _validate_course_lesson(db, payload.get("course_id"), payload.get("lesson_id"))

    # Cross-field date check (agar bittasi yangilangan bo'lsa)
    new_start = payload.get("scheduled_start", session.scheduled_start)
    new_end = payload.get("scheduled_end", session.scheduled_end)
    if new_end <= new_start:
        raise ValidationError("scheduled_end scheduled_start dan keyin bo'lishi shart")

    for k, v in payload.items():
        setattr(session, k, v)
    await db.flush()
    await db.refresh(session)
    return session


async def delete_session(db: AsyncSession, session_id: int) -> None:
    session = await get_session(db, session_id)
    if session.status == "live":
        raise ConflictError("Boshlangan sessionni o'chirib bo'lmaydi (avval tugating)")
    await db.delete(session)
    await db.flush()


# ============================================================================
# Status transitions
# ============================================================================


def _check_transition(current: str, target: str) -> None:
    allowed = LIVE_TRANSITIONS.get(current, set())
    if target not in allowed:
        allowed_str = ", ".join(sorted(allowed)) if allowed else "yo'q"
        raise ConflictError(
            f"Status o'tishi taqiqlangan: '{current}' → '{target}' "
            f"(ruxsat etilgan: {allowed_str})"
        )


async def start_session(db: AsyncSession, session_id: int) -> LiveSession:
    session = await get_session(db, session_id)
    _check_transition(session.status, "live")
    session.status = "live"
    session.actual_start = _now()
    await db.flush()
    await db.refresh(session)
    return session


async def end_session(db: AsyncSession, session_id: int) -> LiveSession:
    session = await get_session(db, session_id)
    _check_transition(session.status, "ended")
    session.status = "ended"
    session.actual_end = _now()

    # Davomat finalizatsiyasi — ochiq attendance yozuvlarini yopish
    open_atts = (
        await db.execute(
            select(LiveAttendance).where(
                LiveAttendance.session_id == session_id,
                LiveAttendance.left_at.is_(None),
                LiveAttendance.joined_at.isnot(None),
            )
        )
    ).scalars().all()
    for att in open_atts:
        att.left_at = session.actual_end
        if att.joined_at is not None:
            delta = (att.left_at - att.joined_at).total_seconds()
            att.total_minutes = max(att.total_minutes, int(delta // 60))
        _recompute_counted(att, session)

    await db.flush()
    await db.refresh(session)
    return session


async def cancel_session(db: AsyncSession, session_id: int) -> LiveSession:
    session = await get_session(db, session_id)
    _check_transition(session.status, "cancelled")
    session.status = "cancelled"
    await db.flush()
    await db.refresh(session)
    return session


# ============================================================================
# Attendance (join / leave)
# ============================================================================


async def _get_or_create_attendance(
    db: AsyncSession, session_id: int, user_id: int
) -> LiveAttendance:
    stmt = select(LiveAttendance).where(
        LiveAttendance.session_id == session_id,
        LiveAttendance.user_id == user_id,
    )
    att = (await db.execute(stmt)).scalar_one_or_none()
    if att is None:
        att = LiveAttendance(session_id=session_id, user_id=user_id)
        db.add(att)
        await db.flush()
        await db.refresh(att)
    return att


def _recompute_counted(att: LiveAttendance, session: LiveSession) -> None:
    """75% qoidasi: scheduled duration ga nisbatan total_minutes ulushi."""
    if session.duration_minutes <= 0:
        att.is_counted = False
        return
    pct = (att.total_minutes / session.duration_minutes) * 100
    att.is_counted = pct >= session.min_attendance_percent


def effective_minutes(att: LiveAttendance, session: LiveSession) -> int:
    """Ko'rsatish uchun jonli daqiqalar.

    Ishtirokchi hozir ulanib tursa (joined_at bor, left_at yo'q, session live),
    o'tib ketgan vaqtni ham qo'shadi — aks holda davomat panelida "0 min" turardi.
    """
    base = att.total_minutes
    if (
        att.joined_at is not None
        and att.left_at is None
        and session.status == "live"
    ):
        delta = (_now() - att.joined_at).total_seconds()
        return max(base, int(delta // 60))
    return base


async def mark_join(
    db: AsyncSession, session_id: int, user_id: int
) -> LiveAttendance:
    session = await get_session(db, session_id)
    if session.status != "live":
        raise ConflictError("Session aktiv emas (status='live' bo'lishi shart)")
    att = await _get_or_create_attendance(db, session_id, user_id)
    if att.joined_at is None:
        att.joined_at = _now()
    # Reconnect: joined_at tushib qoldi, lekin already joined — left_at ni reset
    att.left_at = None
    await db.flush()
    await db.refresh(att)
    return att


async def mark_leave(
    db: AsyncSession, session_id: int, user_id: int
) -> LiveAttendance:
    session = await get_session(db, session_id)
    stmt = select(LiveAttendance).where(
        LiveAttendance.session_id == session_id,
        LiveAttendance.user_id == user_id,
    )
    att = (await db.execute(stmt)).scalar_one_or_none()
    if att is None or att.joined_at is None:
        raise ConflictError("Foydalanuvchi sessionga qo'shilmagan")

    att.left_at = _now()
    delta = (att.left_at - att.joined_at).total_seconds()
    # Increment yoki overwrite — agar reconnect bo'lsa, bir sessiya davomida
    # max bo'lib turish kerak (oddiy implementation: maksimumi)
    att.total_minutes = max(att.total_minutes, int(delta // 60))
    _recompute_counted(att, session)
    await db.flush()
    await db.refresh(att)
    return att


# ============================================================================
# Attendance list (with user metadata)
# ============================================================================


async def list_attendance(
    db: AsyncSession, session_id: int
) -> list[tuple[LiveAttendance, User]]:
    """Sessiyaning davomat ro'yxati — user (full_name, email) bilan birga."""
    await get_session(db, session_id)  # 404 check
    stmt = (
        select(LiveAttendance, User)
        .join(User, User.id == LiveAttendance.user_id)
        .where(LiveAttendance.session_id == session_id)
        .order_by(LiveAttendance.id)
    )
    rows = (await db.execute(stmt)).all()
    return [(att, user) for att, user in rows]


async def attendance_summary(db: AsyncSession, session_id: int) -> dict:
    """Sessiyaning davomat statistikasi (counted/total, foiz)."""
    session = await get_session(db, session_id)
    stmt = select(LiveAttendance).where(LiveAttendance.session_id == session_id)
    items = list((await db.execute(stmt)).scalars().all())
    total = len(items)
    joined = sum(1 for a in items if a.joined_at is not None)
    counted = sum(1 for a in items if a.is_counted)
    avg_minutes = (
        sum(effective_minutes(a, session) for a in items) / total
        if total > 0
        else 0.0
    )
    counted_pct = (counted / joined * 100) if joined > 0 else 0.0
    return {
        "session_id": session.id,
        "status": session.status,
        "duration_minutes": session.duration_minutes,
        "min_attendance_percent": session.min_attendance_percent,
        "total_participants": total,
        "joined_participants": joined,
        "counted_participants": counted,
        "counted_percent": round(counted_pct, 1),
        "average_minutes": round(avg_minutes, 1),
    }


async def recompute_all_attendance(db: AsyncSession, session_id: int) -> int:
    """Davomatlar ro'yxatini qayta hisoblash (admin/host bulk operation).

    `total_minutes` saqlanadi, lekin `is_counted` qayta tekshiriladi
    (`min_attendance_percent` o'zgargan bo'lsa kerak bo'ladi).
    Qaytaradi — yangilangan satrlar soni.
    """
    session = await get_session(db, session_id)
    stmt = select(LiveAttendance).where(LiveAttendance.session_id == session_id)
    items = list((await db.execute(stmt)).scalars().all())
    for att in items:
        _recompute_counted(att, session)
    await db.flush()
    return len(items)


# ============================================================================
# Join info (provider'ga delegatsiya — Phase 5b)
# ============================================================================


# ----- Waiting room (admission) — Phase 31 -----------------------------------


async def request_admission(
    db: AsyncSession, *, session_id: int, user_id: int
) -> LiveAdmission:
    """Talaba kirish so'rovi — mavjud bo'lsa qaytaradi, bo'lmasa pending yaratadi."""
    adm = (
        await db.execute(
            select(LiveAdmission).where(
                LiveAdmission.session_id == session_id,
                LiveAdmission.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if adm is None:
        adm = LiveAdmission(
            session_id=session_id,
            user_id=user_id,
            status="pending",
            requested_at=_now(),
        )
        db.add(adm)
        await db.flush()
    return adm


async def get_admission_status(
    db: AsyncSession, *, session_id: int, user_id: int
) -> str | None:
    adm = (
        await db.execute(
            select(LiveAdmission.status).where(
                LiveAdmission.session_id == session_id,
                LiveAdmission.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    return adm


async def list_pending_admissions(
    db: AsyncSession, session_id: int
) -> list[tuple[LiveAdmission, User]]:
    rows = (
        await db.execute(
            select(LiveAdmission, User)
            .join(User, User.id == LiveAdmission.user_id)
            .where(
                LiveAdmission.session_id == session_id,
                LiveAdmission.status == "pending",
            )
            .order_by(LiveAdmission.requested_at)
        )
    ).all()
    return [(a, u) for a, u in rows]


async def decide_admission(
    db: AsyncSession, *, session_id: int, user_id: int, approve: bool
) -> LiveAdmission:
    adm = (
        await db.execute(
            select(LiveAdmission).where(
                LiveAdmission.session_id == session_id,
                LiveAdmission.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if adm is None:
        raise NotFoundError("Kirish so'rovi topilmadi")
    adm.status = "approved" if approve else "denied"
    adm.decided_at = _now()
    await db.flush()
    return adm


async def attach_recording(
    db: AsyncSession,
    session_id: int,
    *,
    recording_url: str,
    mime_type: str,
    size_bytes: int,
    duration_seconds: int | None,
    thumbnail_url: str | None,
) -> LiveSession:
    """Recording metadata'sini LiveSession'ga biriktirish.

    Eski recording bo'lsa overwrite qiladi (caller eski faylni MinIO'dan
    o'chirib qo'yishi kerak).
    """
    session = await get_session(db, session_id)
    session.recording_url = recording_url
    session.recording_mime_type = mime_type
    session.recording_size_bytes = size_bytes
    session.recording_duration_seconds = duration_seconds
    session.thumbnail_url = thumbnail_url
    await db.flush()
    await db.refresh(session)
    return session


async def detach_recording(db: AsyncSession, session_id: int) -> LiveSession:
    """Recording maydonlarini tozalash (faylni MinIO'dan o'chirish — caller)."""
    session = await get_session(db, session_id)
    session.recording_url = None
    session.recording_mime_type = None
    session.recording_size_bytes = None
    session.recording_duration_seconds = None
    session.thumbnail_url = None
    await db.flush()
    await db.refresh(session)
    return session


def room_name_for(session: LiveSession) -> str:
    """LiveKit xona nomi — admin operatsiyalari (delete/update) uchun."""
    provider = get_provider(session.provider)
    return session.provider_meeting_id or provider.make_room_name(session.id)


def build_join_info(session: LiveSession, *, user: User) -> dict:
    """Provider-specific token + URL ni qaytaradi.

    Provider tanlovi `session.provider` orqali. Har provider'ning JWT/checksum
    logikasi `app.modules.live.providers` ichida.
    """
    is_host = session.host_user_id == user.id
    provider = get_provider(session.provider)
    room_name = session.provider_meeting_id or provider.make_room_name(session.id)

    info = provider.build_join_info(
        room_name=room_name,
        user=ProviderUser(
            id=user.id,
            name=user.full_name,
            email=user.email,
            is_host=is_host,
        ),
    )
    return {
        "session_id": session.id,
        "provider": info.provider,
        "room_name": info.room_name,
        "join_url": info.join_url,
        "is_host": is_host,
        "embed_token": info.embed_token,
        "embed_config": info.embed_config,
    }

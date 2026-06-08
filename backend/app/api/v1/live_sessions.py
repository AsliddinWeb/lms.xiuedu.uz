"""Live darslar endpointlari (Phase 5a).

Endpoints (10):
- GET    /live-sessions                          ro'yxat (filter: status, course_id, host_user_id, sana)
- POST   /live-sessions                          yaratish
- GET    /live-sessions/{id}                     bitta
- PATCH  /live-sessions/{id}                     tahrir
- DELETE /live-sessions/{id}                     o'chirish (cancelled bo'lmasa)
- POST   /live-sessions/{id}/start               status: scheduled → live
- POST   /live-sessions/{id}/end                 status: live → ended
- POST   /live-sessions/{id}/cancel              status: scheduled|live → cancelled
- GET    /live-sessions/{id}/join-info           join URL + provider token (5b da)
- POST   /live-sessions/{id}/join                attendance.joined_at qayd qiladi
- POST   /live-sessions/{id}/leave               attendance.left_at + total_minutes
- GET    /live-sessions/{id}/attendance          davomat ro'yxati (host/admin)
"""

from __future__ import annotations

import asyncio
import secrets
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import PlainTextResponse
from sqlalchemy import select

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.storage import (
    delete_object,
    get_presigned_url,
    object_key_from_url,
    upload_object,
)
from app.modules.auth.dependencies import (
    CurrentUser,
    DbSession,
    RedisClient,
    require_permission,
)
from app.modules.live import captions as captions_service
from app.modules.live import egress as egress_service
from app.modules.live import recordings as recordings_service
from app.modules.live import service
from app.modules.live.ical import (
    build_ics,
    make_calendar_token,
    verify_calendar_token,
)
from app.modules.live.models import LiveRecording, LiveSession
from app.modules.live.recording import (
    ALLOWED_RECORDING_MIME,
    RECORDING_HARD_MAX_BYTES,
    generate_thumbnail,
    probe_duration_seconds,
)
from app.modules.live.schemas import (
    AttendanceSummary,
    CalendarTokenResponse,
    LiveAdmissionDecision,
    LiveAdmissionItem,
    LiveAttendanceItem,
    LiveAttendancePublic,
    LiveCaptionBatchRequest,
    LiveCaptionPublic,
    LiveJoinInfo,
    LiveRecordingPublic,
    LiveSessionCreateRequest,
    LiveSessionPublic,
    LiveSessionUpdateRequest,
    PaginatedLiveSessions,
)
from app.modules.rbac.service import RBACService, has_permission
from app.modules.users.models import User

router = APIRouter()


def _sign_recording(public: LiveRecordingPublic, object_key: str | None) -> LiveRecordingPublic:
    """Phase 7b — recording URL'ni 15-daqiqalik presigned URL bilan almashtirish."""
    if not object_key:
        return public
    try:
        public.url = get_presigned_url(object_key, ttl_seconds=900)
    except Exception:
        pass
    return public


def _sign_session(public: LiveSessionPublic) -> LiveSessionPublic:
    """Phase 7b — LiveSession.recording_url'ni presigned URL bilan almashtirish."""
    if public.recording_url:
        key = object_key_from_url(public.recording_url)
        if key:
            try:
                public.recording_url = get_presigned_url(key, ttl_seconds=900)
            except Exception:
                pass
    return public


# ============================================================================
# Helpers
# ============================================================================


async def _user_can_manage_session(
    db: DbSession, redis: RedisClient, user: User, session_id: int
) -> bool:
    """Host yoki platform.* permissionga ega user'lar boshqara oladi."""
    session = await service.get_session(db, session_id)
    if session.host_user_id == user.id:
        return True
    rbac = RBACService(db, redis)
    perms = await rbac.get_user_permissions(user.id)
    return has_permission(perms, "platform.*")


# ============================================================================
# CRUD
# ============================================================================


@router.get(
    "/live-sessions",
    response_model=PaginatedLiveSessions,
    summary="Live sessiyalar ro'yxati",
)
async def list_live_sessions(
    db: DbSession,
    _u: User = Depends(require_permission("live.read")),
    status_: str | None = Query(None, alias="status"),
    course_id: int | None = Query(None),
    lesson_id: int | None = Query(None),
    host_user_id: int | None = Query(None),
    starts_after: datetime | None = Query(None),
    starts_before: datetime | None = Query(None),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedLiveSessions:
    items, total = await service.list_sessions(
        db,
        status_=status_,
        course_id=course_id,
        lesson_id=lesson_id,
        host_user_id=host_user_id,
        starts_after=starts_after,
        starts_before=starts_before,
        q=q,
        page=page,
        page_size=page_size,
    )
    pubs = [_sign_session(LiveSessionPublic.model_validate(s)) for s in items]
    # Host nomlarini bitta so'rovda to'ldiramiz (admin/talaba ro'yxati uchun)
    if pubs:
        from sqlalchemy import select as _select

        host_ids = {p.host_user_id for p in pubs}
        rows = (
            await db.execute(
                _select(User.id, User.full_name).where(User.id.in_(host_ids))
            )
        ).all()
        names = {uid: fn for uid, fn in rows}
        for p in pubs:
            p.host_full_name = names.get(p.host_user_id)
    return PaginatedLiveSessions(items=pubs, total=total)


@router.post(
    "/live-sessions",
    response_model=LiveSessionPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi live session yaratish (status='scheduled')",
)
async def create_live_session(
    data: LiveSessionCreateRequest,
    db: DbSession,
    actor: CurrentUser,
    _u: User = Depends(require_permission("live.host")),
) -> LiveSessionPublic:
    session = await service.create_session(db, data, host_user_id=actor.id)
    await db.commit()
    return _sign_session(LiveSessionPublic.model_validate(session))


@router.get("/live-sessions/{session_id}", response_model=LiveSessionPublic)
async def get_live_session(
    session_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("live.read")),
) -> LiveSessionPublic:
    return _sign_session(LiveSessionPublic.model_validate(await service.get_session(db, session_id)))


@router.patch("/live-sessions/{session_id}", response_model=LiveSessionPublic)
async def update_live_session(
    session_id: int,
    data: LiveSessionUpdateRequest,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("live.host")),
) -> LiveSessionPublic:
    if not await _user_can_manage_session(db, redis, actor, session_id):
        raise ForbiddenError("Bu sessionni tahrirlash huquqi yo'q")
    session = await service.update_session(db, session_id, data)
    await db.commit()
    return _sign_session(LiveSessionPublic.model_validate(session))


@router.delete(
    "/live-sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_live_session(
    session_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("live.host")),
) -> Response:
    if not await _user_can_manage_session(db, redis, actor, session_id):
        raise ForbiddenError("Bu sessionni o'chirish huquqi yo'q")
    await service.delete_session(db, session_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Status transitions
# ============================================================================


@router.post("/live-sessions/{session_id}/start", response_model=LiveSessionPublic)
async def start_live_session(
    session_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("live.host")),
) -> LiveSessionPublic:
    if not await _user_can_manage_session(db, redis, actor, session_id):
        raise ForbiddenError("Faqat host yoki super_admin sessionni boshlay oladi")
    session = await service.start_session(db, session_id)
    await db.commit()
    return _sign_session(LiveSessionPublic.model_validate(session))


@router.post("/live-sessions/{session_id}/end", response_model=LiveSessionPublic)
async def end_live_session(
    session_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("live.host")),
) -> LiveSessionPublic:
    if not await _user_can_manage_session(db, redis, actor, session_id):
        raise ForbiddenError("Faqat host yoki super_admin sessionni tugata oladi")
    session = await service.end_session(db, session_id)
    await db.commit()
    return _sign_session(LiveSessionPublic.model_validate(session))


@router.post("/live-sessions/{session_id}/cancel", response_model=LiveSessionPublic)
async def cancel_live_session(
    session_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("live.host")),
) -> LiveSessionPublic:
    if not await _user_can_manage_session(db, redis, actor, session_id):
        raise ForbiddenError("Faqat host yoki super_admin sessionni bekor qila oladi")
    session = await service.cancel_session(db, session_id)
    await db.commit()
    return _sign_session(LiveSessionPublic.model_validate(session))


# ============================================================================
# Join / Leave
# ============================================================================


@router.get(
    "/live-sessions/{session_id}/join-info",
    response_model=LiveJoinInfo,
    summary="Provider URL va token (host yoki ishtirokchi olishi mumkin)",
)
async def get_join_info(
    session_id: int,
    db: DbSession,
    actor: CurrentUser,
    _u: User = Depends(require_permission("live.read")),
) -> LiveJoinInfo:
    session = await service.get_session(db, session_id)
    info = service.build_join_info(session, user=actor)
    is_host = session.host_user_id == actor.id
    # Waiting room — host emas va tasdiq talab qilinsa, token bermaymiz
    if session.requires_approval and not is_host and session.status == "live":
        adm_status = await service.get_admission_status(
            db, session_id=session_id, user_id=actor.id
        )
        if adm_status != "approved":
            await service.request_admission(
                db, session_id=session_id, user_id=actor.id
            )
            await db.commit()
            return LiveJoinInfo(
                session_id=session_id,
                provider=session.provider,
                room_name=info["room_name"],
                join_url=info["join_url"],
                is_host=False,
                embed_token=None,
                embed_config=None,
                pending=True,
            )
    return LiveJoinInfo(**info)


# ----- Waiting room (admission) — Phase 31 -----------------------------------


@router.get(
    "/live-sessions/{session_id}/admissions",
    response_model=list[LiveAdmissionItem],
    summary="Kutayotgan kirish so'rovlari (host)",
)
async def list_admissions(
    session_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("live.host")),
) -> list[LiveAdmissionItem]:
    if not await _user_can_manage_session(db, redis, actor, session_id):
        raise ForbiddenError("Kirish so'rovlarini ko'rish huquqi yo'q")
    rows = await service.list_pending_admissions(db, session_id)
    return [
        LiveAdmissionItem(
            user_id=u.id,
            full_name=u.full_name,
            email=u.email,
            status=a.status,
            requested_at=a.requested_at,
        )
        for a, u in rows
    ]


@router.post(
    "/live-sessions/{session_id}/admissions/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Kirish so'rovini tasdiqlash/rad etish (host)",
)
async def decide_admission(
    session_id: int,
    user_id: int,
    payload: LiveAdmissionDecision,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("live.host")),
) -> Response:
    if not await _user_can_manage_session(db, redis, actor, session_id):
        raise ForbiddenError("Kirish so'rovini hal qilish huquqi yo'q")
    await service.decide_admission(
        db, session_id=session_id, user_id=user_id, approve=payload.approve
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/live-sessions/{session_id}/join",
    response_model=LiveAttendancePublic,
    summary="Sessionga qo'shilganlikni qayd qilish (joined_at)",
)
async def join_live_session(
    session_id: int,
    db: DbSession,
    actor: CurrentUser,
    _u: User = Depends(require_permission("live.join")),
) -> LiveAttendancePublic:
    att = await service.mark_join(db, session_id, actor.id)
    await db.commit()
    return LiveAttendancePublic.model_validate(att)


@router.post(
    "/live-sessions/{session_id}/leave",
    response_model=LiveAttendancePublic,
    summary="Sessiondan chiqish (left_at + total_minutes)",
)
async def leave_live_session(
    session_id: int,
    db: DbSession,
    actor: CurrentUser,
    _u: User = Depends(require_permission("live.join")),
) -> LiveAttendancePublic:
    att = await service.mark_leave(db, session_id, actor.id)
    await db.commit()
    return LiveAttendancePublic.model_validate(att)


# ============================================================================
# Attendance list
# ============================================================================


@router.get(
    "/live-sessions/{session_id}/attendance",
    response_model=list[LiveAttendanceItem],
    summary="Sessiyaning davomat ro'yxati (host yoki admin)",
)
async def list_session_attendance(
    session_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("live.read")),
) -> list[LiveAttendanceItem]:
    # Faqat host yoki platform.* — talaba boshqalarning davomatini ko'rmaydi
    if not await _user_can_manage_session(db, redis, actor, session_id):
        raise ForbiddenError("Davomat ro'yxatini ko'rish huquqi yo'q")
    rows = await service.list_attendance(db, session_id)
    return [
        LiveAttendanceItem(
            user_id=user.id,
            full_name=user.full_name,
            email=user.email,
            joined_at=att.joined_at,
            left_at=att.left_at,
            total_minutes=att.total_minutes,
            is_counted=att.is_counted,
        )
        for att, user in rows
    ]


# ============================================================================
# Recording (Phase 5d)
# ============================================================================


@router.post(
    "/live-sessions/{session_id}/recording-upload",
    response_model=LiveSessionPublic,
    summary="Recording faylini yuklash (host yoki admin). MP4/WebM/MKV/MOV.",
)
async def upload_recording(
    session_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("live.host")),
    file: UploadFile = File(..., description="Recording video fayli"),
) -> LiveSessionPublic:
    if not await _user_can_manage_session(db, redis, actor, session_id):
        raise ForbiddenError("Bu sessionga recording yuklash huquqi yo'q")

    session = await service.get_session(db, session_id)

    # MIME tekshiruvi
    ctype = (file.content_type or "application/octet-stream").lower()
    if ctype not in ALLOWED_RECORDING_MIME:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Recording format qo'llab-quvvatlanmaydi: {ctype}",
        )

    # Faylni temp diskga yozamiz (RAM'ga yuklamasdan ffprobe/ffmpeg chaqirish uchun)
    suffix = Path(file.filename or "rec.mp4").suffix.lower() or ".mp4"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = Path(tmp.name)
        size = 0
        try:
            while True:
                chunk = await file.read(8 * 1024 * 1024)  # 8 MB
                if not chunk:
                    break
                size += len(chunk)
                if size > RECORDING_HARD_MAX_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=(
                            f"Recording {RECORDING_HARD_MAX_BYTES // (1024 * 1024)} "
                            f"MB dan oshmasligi kerak"
                        ),
                    )
                tmp.write(chunk)
        except HTTPException:
            tmp_path.unlink(missing_ok=True)
            raise

    try:
        # ffprobe + ffmpeg event-loopni bloklamasin (worker thread'da)
        duration, thumb_bytes = await asyncio.gather(
            asyncio.to_thread(probe_duration_seconds, tmp_path),
            asyncio.to_thread(generate_thumbnail, tmp_path),
        )

        # MinIO upload (video) — sync I/O ham thread'ga uzatamiz
        ext = suffix.lstrip(".") or "mp4"
        object_name = (
            f"recordings/{session_id}/{secrets.token_hex(8)}.{ext}"
        )
        data = await asyncio.to_thread(tmp_path.read_bytes)
        recording_url = await asyncio.to_thread(
            upload_object, object_name=object_name, data=data, content_type=ctype
        )

        # MinIO upload (thumbnail — agar yaratilgan bo'lsa)
        thumbnail_url: str | None = None
        if thumb_bytes:
            thumb_name = f"thumbnails/{session_id}/{secrets.token_hex(8)}.jpg"
            thumbnail_url = await asyncio.to_thread(
                upload_object,
                object_name=thumb_name,
                data=thumb_bytes,
                content_type="image/jpeg",
            )

        # Eski recording bo'lsa MinIO'dan o'chiramiz
        if session.recording_url:
            old_key = object_key_from_url(session.recording_url)
            if old_key:
                delete_object(old_key)
        if session.thumbnail_url:
            old_thumb = object_key_from_url(session.thumbnail_url)
            if old_thumb:
                delete_object(old_thumb)

        updated = await service.attach_recording(
            db,
            session_id,
            recording_url=recording_url,
            mime_type=ctype,
            size_bytes=size,
            duration_seconds=duration,
            thumbnail_url=thumbnail_url,
        )
        await db.commit()
        return _sign_session(LiveSessionPublic.model_validate(updated))
    finally:
        tmp_path.unlink(missing_ok=True)


@router.delete(
    "/live-sessions/{session_id}/recording",
    response_model=LiveSessionPublic,
    summary="Recording faylini o'chirish (host yoki admin)",
)
async def delete_recording(
    session_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("live.host")),
) -> LiveSessionPublic:
    if not await _user_can_manage_session(db, redis, actor, session_id):
        raise ForbiddenError("Bu sessionning recording'ini o'chirish huquqi yo'q")
    session = await service.get_session(db, session_id)
    if session.recording_url:
        key = object_key_from_url(session.recording_url)
        if key:
            delete_object(key)
    if session.thumbnail_url:
        tkey = object_key_from_url(session.thumbnail_url)
        if tkey:
            delete_object(tkey)
    updated = await service.detach_recording(db, session_id)
    await db.commit()
    return _sign_session(LiveSessionPublic.model_validate(updated))


# ============================================================================
# Attendance summary + recompute (Phase 5e)
# ============================================================================


@router.get(
    "/live-sessions/{session_id}/attendance/summary",
    response_model=AttendanceSummary,
    summary="Davomat statistikasi (host yoki admin)",
)
async def get_attendance_summary(
    session_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("live.read")),
) -> AttendanceSummary:
    if not await _user_can_manage_session(db, redis, actor, session_id):
        raise ForbiddenError("Davomat statistikasini ko'rish huquqi yo'q")
    summary = await service.attendance_summary(db, session_id)
    return AttendanceSummary(**summary)


@router.post(
    "/live-sessions/{session_id}/attendance/recompute",
    response_model=AttendanceSummary,
    summary="Davomat is_counted'ni qayta hisoblash (host yoki admin)",
)
async def recompute_attendance(
    session_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("live.host")),
) -> AttendanceSummary:
    if not await _user_can_manage_session(db, redis, actor, session_id):
        raise ForbiddenError("Davomatni qayta hisoblash huquqi yo'q")
    await service.recompute_all_attendance(db, session_id)
    await db.commit()
    summary = await service.attendance_summary(db, session_id)
    return AttendanceSummary(**summary)


# ============================================================================
# iCal export (Phase 5e)
# ============================================================================


@router.get(
    "/live-calendar/token",
    response_model=CalendarTokenResponse,
    summary="Shaxsiy iCal subscribe URL'ni olish",
)
async def get_calendar_token(
    request: Request,
    actor: CurrentUser,
    _u: User = Depends(require_permission("live.read")),
) -> CalendarTokenResponse:
    token = make_calendar_token(actor.id)
    url = str(
        request.url_for("live_calendar_ics").include_query_params(
            user=actor.id, token=token
        )
    )
    return CalendarTokenResponse(url=url, token=token)


@router.get(
    "/live-calendar.ics",
    name="live_calendar_ics",
    response_class=PlainTextResponse,
    summary="iCal feed (token bilan, kalendar app subscribe qiladi)",
    include_in_schema=False,
)
async def calendar_ics(
    db: DbSession,
    user: int = Query(..., description="User ID"),
    token: str = Query(..., description="Calendar HMAC token"),
) -> PlainTextResponse:
    if not verify_calendar_token(user, token):
        raise NotFoundError("Calendar feed topilmadi")
    # Foydalanuvchining kelajakdagi va shu hafta tugagan sessiyalari:
    # host bo'lganlari + qatnashgan sessiyalari (LiveAttendance bo'yicha)
    from app.modules.live.models import LiveAttendance

    own_stmt = select(LiveSession).where(
        LiveSession.host_user_id == user,
        LiveSession.status.in_(("scheduled", "live", "ended")),
    )
    own_sessions = list((await db.execute(own_stmt)).scalars().all())

    joined_stmt = (
        select(LiveSession)
        .join(LiveAttendance, LiveAttendance.session_id == LiveSession.id)
        .where(
            LiveAttendance.user_id == user,
            LiveSession.status.in_(("scheduled", "live", "ended")),
        )
    )
    joined_sessions = list((await db.execute(joined_stmt)).scalars().all())

    # Dedupe by id
    by_id: dict[int, LiveSession] = {s.id: s for s in own_sessions}
    for s in joined_sessions:
        by_id.setdefault(s.id, s)
    sessions = sorted(by_id.values(), key=lambda s: s.scheduled_start)

    body = build_ics(sessions)
    return PlainTextResponse(
        content=body,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": 'inline; filename="xiu-live.ics"',
            "Cache-Control": "no-store",
        },
    )


# ============================================================================
# Recordings (Phase 7a)
# ============================================================================


@router.post(
    "/live-sessions/{session_id}/recordings/start",
    response_model=LiveRecordingPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi recording boshlash (pedagog)",
)
async def start_recording(
    session_id: int,
    db: DbSession,
    user: CurrentUser,
    _u: User = Depends(require_permission("live.host")),
) -> LiveRecordingPublic:
    rec = await recordings_service.start_recording(db, session_id, user_id=user.id)
    await db.commit()
    await db.refresh(rec)
    return _sign_recording(LiveRecordingPublic.model_validate(rec), rec.object_key)


@router.post(
    "/live-recordings/{recording_id}/upload",
    response_model=LiveRecordingPublic,
    summary="MediaRecorder blob'ni yuklash (pedagog stop bosganda)",
)
async def upload_recording(
    recording_id: int,
    db: DbSession,
    user: CurrentUser,
    blob: UploadFile = File(...),
    duration_seconds: int | None = Query(default=None),
    _u: User = Depends(require_permission("live.host")),
) -> LiveRecordingPublic:
    raw = await blob.read()
    rec = await recordings_service.upload_blob(
        db,
        recording_id,
        user_id=user.id,
        blob=raw,
        content_type=blob.content_type or "video/webm",
        duration_seconds=duration_seconds,
    )
    await db.commit()
    await db.refresh(rec)
    return _sign_recording(LiveRecordingPublic.model_validate(rec), rec.object_key)


@router.get(
    "/live-sessions/{session_id}/recordings",
    response_model=list[LiveRecordingPublic],
    summary="Sessionning barcha yozuvlari (talaba ham ko'radi)",
)
async def list_recordings(
    session_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("live.read")),
) -> list[LiveRecordingPublic]:
    items = await recordings_service.list_for_session(db, session_id)
    out: list[LiveRecordingPublic] = []
    for r in items:
        out.append(_sign_recording(LiveRecordingPublic.model_validate(r), r.object_key))
    return out


@router.delete(
    "/live-recordings/{recording_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Yozuvni o'chirish (pedagog)",
)
async def delete_recording(
    recording_id: int,
    db: DbSession,
    user: CurrentUser,
    _u: User = Depends(require_permission("live.host")),
) -> Response:
    await recordings_service.delete_recording(db, recording_id, user_id=user.id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Server-side recording (LiveKit Egress) — Phase 32
# ============================================================================


@router.post(
    "/live-sessions/{session_id}/egress/start",
    response_model=LiveRecordingPublic,
    summary="Server yozuvini boshlash (egress, host)",
)
async def egress_start(
    session_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("live.host")),
) -> LiveRecordingPublic:
    if not await _user_can_manage_session(db, redis, actor, session_id):
        raise ForbiddenError("Yozuvni boshlash huquqi yo'q")
    session = await service.get_session(db, session_id)
    if session.status != "live":
        raise ConflictError("Faqat jonli sessiyani yozish mumkin")
    # Allaqachon faol egress yozuvi bormi?
    existing = (
        await db.execute(
            select(LiveRecording).where(
                LiveRecording.session_id == session_id,
                LiveRecording.status == "recording",
                LiveRecording.egress_id.isnot(None),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return _sign_recording(
            LiveRecordingPublic.model_validate(existing), existing.object_key
        )

    object_key = f"recordings/{session_id}/egress-{secrets.token_hex(6)}.mp4"
    room = session.provider_meeting_id or service.get_provider(
        session.provider
    ).make_room_name(session.id)
    try:
        egress_id = await egress_service.start_room_composite(room, object_key)
    except Exception as exc:  # noqa: BLE001 — twirp xatolari (xona faol emas, ...)
        raise ConflictError(
            "Server yozuvini boshlab bo'lmadi — xonada faol ishtirokchi yo'q "
            "yoki egress xizmati mavjud emas. Avval darsni boshlang."
        ) from exc

    rec = LiveRecording(
        session_id=session_id,
        recorded_by=actor.id,
        status="recording",
        object_key=object_key,
        egress_id=egress_id,
        mime_type="video/mp4",
        started_at=datetime.now(UTC),
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return _sign_recording(LiveRecordingPublic.model_validate(rec), rec.object_key)


@router.post(
    "/live-sessions/{session_id}/egress/stop",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Server yozuvini to'xtatish (egress, host)",
)
async def egress_stop(
    session_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("live.host")),
) -> Response:
    if not await _user_can_manage_session(db, redis, actor, session_id):
        raise ForbiddenError("Yozuvni to'xtatish huquqi yo'q")
    rec = (
        await db.execute(
            select(LiveRecording)
            .where(
                LiveRecording.session_id == session_id,
                LiveRecording.status == "recording",
                LiveRecording.egress_id.isnot(None),
            )
            .order_by(LiveRecording.started_at.desc())
        )
    ).scalars().first()
    if rec is not None and rec.egress_id:
        try:
            await egress_service.stop(rec.egress_id)
        except Exception:  # noqa: BLE001 — webhook baribir finalize qiladi
            pass
        rec.status = "stopping"
        await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Captions (Phase 9c)
# ============================================================================


@router.post(
    "/live-sessions/{session_id}/captions/batch",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Real-time subtitle batch'ni saqlash (pedagog)",
)
async def post_captions_batch(
    session_id: int,
    payload: LiveCaptionBatchRequest,
    db: DbSession,
    user: CurrentUser,
    _u: User = Depends(require_permission("live.host")),
) -> dict:
    inserted = await captions_service.add_batch(
        db,
        session_id,
        [i.model_dump() for i in payload.items],
        speaker_user_id=user.id,
    )
    await db.commit()
    return {"inserted": inserted}


@router.get(
    "/live-sessions/{session_id}/captions",
    response_model=list[LiveCaptionPublic],
    summary="Session subtitle ro'yxati (talaba ham ko'radi)",
)
async def list_captions(
    session_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("live.read")),
) -> list[LiveCaptionPublic]:
    items = await captions_service.list_for_session(db, session_id)
    return [LiveCaptionPublic.model_validate(c) for c in items]


@router.get(
    "/live-sessions/{session_id}/captions.vtt",
    response_class=PlainTextResponse,
    summary="WebVTT formatda subtitle fayli (video <track> uchun)",
    include_in_schema=False,
)
async def captions_vtt(
    session_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("live.read")),
) -> PlainTextResponse:
    body = await captions_service.build_vtt(db, session_id)
    return PlainTextResponse(
        content=body,
        media_type="text/vtt; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )

"""Live recording service — Phase 7a.

Pedagog brauzerida MediaRecorder API orqali olingan video blob'ni MinIO'ga
yuklash + metadata yozish.

Flow:
    1. POST /live/{session_id}/recordings/start     → DB row (status=recording, started_at=now)
    2. (mijoz tarafda MediaRecorder ishlaydi)
    3. POST /live/recordings/{id}/upload            → multipart blob, MinIO save
                                                       → status=finalized, file_url, duration, size
    4. GET  /live/{session_id}/recordings           → ro'yxat
    5. DELETE /live/recordings/{id}                 → pedagog/admin o'chiradi

Bucket: lms-files, key: recordings/live/{session_id}/{rec_id}.webm
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.storage import upload_object
from app.modules.live.models import LiveRecording, LiveSession


def _now() -> datetime:
    return datetime.now(UTC)


async def _get_session(db: AsyncSession, session_id: int) -> LiveSession:
    s = (
        await db.execute(
            select(LiveSession).where(LiveSession.id == session_id)
        )
    ).scalar_one_or_none()
    if s is None:
        raise NotFoundError("Live session topilmadi")
    return s


async def _get_recording(db: AsyncSession, recording_id: int) -> LiveRecording:
    r = (
        await db.execute(
            select(LiveRecording).where(LiveRecording.id == recording_id)
        )
    ).scalar_one_or_none()
    if r is None:
        raise NotFoundError("Yozuv topilmadi")
    return r


def _check_host(session: LiveSession, user_id: int) -> None:
    if session.host_user_id != user_id:
        raise ForbiddenError("Faqat dars hosti yozuv qila oladi")


async def start_recording(
    db: AsyncSession, session_id: int, *, user_id: int
) -> LiveRecording:
    session = await _get_session(db, session_id)
    _check_host(session, user_id)

    # Allaqachon ochiq yozuv bo'lmasligini tekshirish
    existing_open = (
        await db.execute(
            select(LiveRecording).where(
                LiveRecording.session_id == session_id,
                LiveRecording.status == "recording",
            )
        )
    ).scalar_one_or_none()
    if existing_open is not None:
        # Idempotent — qaytaramiz
        return existing_open

    rec = LiveRecording(
        session_id=session_id,
        recorded_by=user_id,
        status="recording",
        started_at=_now(),
    )
    db.add(rec)
    await db.flush()
    return rec


async def upload_blob(
    db: AsyncSession,
    recording_id: int,
    *,
    user_id: int,
    blob: bytes,
    content_type: str = "video/webm",
    duration_seconds: int | None = None,
) -> LiveRecording:
    """Pedagog MediaRecorder stop bo'lganda chaqiriladi — to'liq blob keladi."""
    rec = await _get_recording(db, recording_id)
    session = await _get_session(db, rec.session_id)
    _check_host(session, user_id)

    if rec.status == "finalized":
        raise ConflictError("Yozuv allaqachon yakunlangan")
    if not blob:
        raise ConflictError("Bo'sh blob")

    # MinIO upload
    ext = "webm" if "webm" in content_type else "mp4"
    key = f"recordings/live/{session.id}/{rec.id}_{secrets.token_hex(4)}.{ext}"
    url = upload_object(object_name=key, data=blob, content_type=content_type)

    rec.object_key = key
    rec.url = url
    rec.mime_type = content_type
    rec.file_size_bytes = len(blob)
    rec.duration_seconds = duration_seconds
    rec.finalized_at = _now()
    rec.status = "finalized"

    # LiveSession.recording_url ham yangilash (eski Phase 5d field bilan moslashtirish)
    session.recording_url = url
    session.recording_size_bytes = len(blob)
    session.recording_duration_seconds = duration_seconds
    session.recording_mime_type = content_type

    await db.flush()
    return rec


async def list_for_session(
    db: AsyncSession, session_id: int
) -> list[LiveRecording]:
    stmt = (
        select(LiveRecording)
        .where(LiveRecording.session_id == session_id)
        .order_by(LiveRecording.started_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def delete_recording(
    db: AsyncSession, recording_id: int, *, user_id: int
) -> None:
    rec = await _get_recording(db, recording_id)
    session = await _get_session(db, rec.session_id)
    _check_host(session, user_id)
    # MinIO'dan ham o'chirish (kelajakda — hozir orphan qoldiramiz)
    await db.delete(rec)
    await db.flush()

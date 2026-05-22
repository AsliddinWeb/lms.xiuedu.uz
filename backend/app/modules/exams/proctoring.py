"""Proctoring service — Phase 6f.

Talaba imtihon yechayotganda yuz beruvchi hodisalarni va kamera snapshotlarini
qayd etadi, violation score hisoblaydi, kerak bo'lsa attempt'ni flag qiladi.

Violation score:
    0–39    : toza
    40–79   : warning (pedagog ko'rib chiqishi mumkin)
    80+     : critical, attempt avtomatik flag qilinadi
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.core.storage import upload_object
from app.modules.exams.models import (
    ExamAttempt,
    IdReferencePhoto,
    ProctoringEvent,
    ProctoringSnapshot,
)

# Event turi → ball og'irligi
VIOLATION_WEIGHTS: dict[str, int] = {
    "tab_switch": 10,
    "visibility_lost": 8,
    "visibility_returned": 0,
    "fullscreen_exit": 15,
    "fullscreen_entered": 0,
    "copy_attempt": 5,
    "paste_attempt": 20,
    "context_menu": 2,
    "face_lost": 5,
    "face_found": 0,
    "multiple_faces": 50,
    "loud_audio": 3,
    "voice_detected": 3,
    "devtools_opened": 30,
    "browser_resized": 1,
    "network_loss": 0,
    "network_restored": 0,
    "manual_flag": 50,
    # Phase 9b — gaze tracking
    "gaze_off": 8,
    "gaze_returned": 0,
}

VALID_EVENT_TYPES = set(VIOLATION_WEIGHTS.keys())
VALID_SEVERITIES = {"info", "warning", "critical"}

FLAG_THRESHOLD = 80


def _now() -> datetime:
    return datetime.now(UTC)


async def _get_attempt(db: AsyncSession, attempt_id: int) -> ExamAttempt:
    attempt = (
        await db.execute(select(ExamAttempt).where(ExamAttempt.id == attempt_id))
    ).scalar_one_or_none()
    if attempt is None:
        raise NotFoundError("Urinish topilmadi")
    return attempt


def _check_owner(attempt: ExamAttempt, user_id: int) -> None:
    if attempt.user_id != user_id:
        raise ForbiddenError("Bu urinish sizga tegishli emas")


async def log_event(
    db: AsyncSession,
    *,
    attempt_id: int,
    user_id: int,
    event_type: str,
    severity: str = "info",
    metadata: dict[str, Any] | None = None,
    occurred_at: datetime | None = None,
) -> ProctoringEvent:
    if event_type not in VALID_EVENT_TYPES:
        raise ValidationError(f"Noma'lum event_type: {event_type}")
    if severity not in VALID_SEVERITIES:
        raise ValidationError(f"Noma'lum severity: {severity}")

    attempt = await _get_attempt(db, attempt_id)
    _check_owner(attempt, user_id)

    event = ProctoringEvent(
        attempt_id=attempt_id,
        event_type=event_type,
        severity=severity,
        event_metadata=metadata,
        occurred_at=occurred_at or _now(),
    )
    db.add(event)
    await db.flush()

    # Score'ni yangilash
    score = await compute_violation_score(db, attempt_id)
    attempt.violation_score = score
    if score >= FLAG_THRESHOLD and not attempt.flagged:
        attempt.flagged = True
    await db.flush()
    return event


async def compute_violation_score(db: AsyncSession, attempt_id: int) -> int:
    """0-100 score qaytaradi.

    Multiple counts of the same event accumulate, but capped at the event's weight × 5.
    """
    stmt = (
        select(ProctoringEvent.event_type, func.count(ProctoringEvent.id))
        .where(ProctoringEvent.attempt_id == attempt_id)
        .group_by(ProctoringEvent.event_type)
    )
    rows = (await db.execute(stmt)).all()

    total = 0
    for event_type, count in rows:
        weight = VIOLATION_WEIGHTS.get(event_type, 0)
        if weight <= 0:
            continue
        # Soft cap: max weight × 5 per event_type
        capped = min(weight * count, weight * 5)
        total += capped

    return min(100, total)


async def list_events(
    db: AsyncSession, attempt_id: int
) -> list[ProctoringEvent]:
    stmt = (
        select(ProctoringEvent)
        .where(ProctoringEvent.attempt_id == attempt_id)
        .order_by(ProctoringEvent.occurred_at.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def upload_snapshot(
    db: AsyncSession,
    *,
    attempt_id: int,
    user_id: int,
    image_bytes: bytes,
    content_type: str = "image/jpeg",
    face_count: int | None = None,
    face_match_score: float | None = None,
    width: int | None = None,
    height: int | None = None,
    captured_at: datetime | None = None,
) -> ProctoringSnapshot:
    attempt = await _get_attempt(db, attempt_id)
    _check_owner(attempt, user_id)

    if not image_bytes:
        raise ValidationError("Bo'sh rasm")

    ext = "jpg" if "jpeg" in content_type or "jpg" in content_type else "png"
    key = f"exams/proctoring/{attempt_id}/snap_{secrets.token_hex(8)}.{ext}"
    url = upload_object(
        object_name=key, data=image_bytes, content_type=content_type
    )

    snapshot = ProctoringSnapshot(
        attempt_id=attempt_id,
        object_key=key,
        url=url,
        face_count=face_count,
        face_match_score=face_match_score,
        width=width,
        height=height,
        bytes_size=len(image_bytes),
        captured_at=captured_at or _now(),
    )
    db.add(snapshot)
    await db.flush()

    # Phase 9a — match_score juda past bo'lsa, "face_mismatch" critical event
    if face_match_score is not None and face_match_score < 0.4 and face_count == 1:
        await log_event(
            db,
            attempt_id=attempt_id,
            user_id=user_id,
            event_type="multiple_faces",  # reuse existing type — yuz boshqa odam
            severity="critical",
            metadata={
                "snapshot_id": snapshot.id,
                "reason": "low_face_match",
                "score": float(face_match_score),
            },
            occurred_at=snapshot.captured_at,
        )

    # face_count anomalies'ni event sifatida ham yozish
    if face_count is not None:
        if face_count == 0:
            await log_event(
                db,
                attempt_id=attempt_id,
                user_id=user_id,
                event_type="face_lost",
                severity="warning",
                metadata={"snapshot_id": snapshot.id},
                occurred_at=snapshot.captured_at,
            )
        elif face_count > 1:
            await log_event(
                db,
                attempt_id=attempt_id,
                user_id=user_id,
                event_type="multiple_faces",
                severity="critical",
                metadata={"snapshot_id": snapshot.id, "count": face_count},
                occurred_at=snapshot.captured_at,
            )

    return snapshot


async def list_snapshots(
    db: AsyncSession, attempt_id: int
) -> list[ProctoringSnapshot]:
    stmt = (
        select(ProctoringSnapshot)
        .where(ProctoringSnapshot.attempt_id == attempt_id)
        .order_by(ProctoringSnapshot.captured_at.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def upload_id_reference(
    db: AsyncSession,
    *,
    attempt_id: int,
    user_id: int,
    image_bytes: bytes,
    content_type: str = "image/jpeg",
) -> IdReferencePhoto:
    """Lobby'da olingan yuz reference rasmi — har attempt uchun 1 ta."""
    attempt = await _get_attempt(db, attempt_id)
    _check_owner(attempt, user_id)

    existing = (
        await db.execute(
            select(IdReferencePhoto).where(IdReferencePhoto.attempt_id == attempt_id)
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("ID rasm allaqachon yuklangan")

    if not image_bytes:
        raise ValidationError("Bo'sh rasm")

    ext = "jpg" if "jpeg" in content_type or "jpg" in content_type else "png"
    key = f"exams/proctoring/{attempt_id}/id_ref.{ext}"
    url = upload_object(
        object_name=key, data=image_bytes, content_type=content_type
    )

    ref = IdReferencePhoto(
        attempt_id=attempt_id,
        object_key=key,
        url=url,
        captured_at=_now(),
    )
    db.add(ref)
    await db.flush()
    return ref


async def get_id_reference(
    db: AsyncSession, attempt_id: int
) -> IdReferencePhoto | None:
    return (
        await db.execute(
            select(IdReferencePhoto).where(IdReferencePhoto.attempt_id == attempt_id)
        )
    ).scalar_one_or_none()

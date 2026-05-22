"""Exam grades HEMIS sync — Phase 7c (real integration + audit log + retry).

Real HemisClient.push_exam_grades chaqiriladi. Har urinish hemis_sync_log
jadvalga yoziladi — admin sahifasidan ko'rish va qayta urinish mumkin.

Trigger:
    - Exam.status `published → archived` bo'lganda + exam.type == 'dak'
    - Yoki POST /exams/{id}/sync-hemis (admin)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError
from app.integrations.hemis.client import HemisClient, HemisError
from app.integrations.hemis.models import HemisSyncLog
from app.integrations.hemis.retry import retry_async
from app.modules.exams.models import Exam, ExamAttempt
from app.modules.users.models import User

logger = logging.getLogger(__name__)


class SyncEntry(TypedDict):
    student_pinfl: str | None
    student_user_id: int
    score: str
    percentage: str
    status: str
    completed_at: str | None


class SyncResult(TypedDict):
    log_id: int
    exam_id: int
    exam_type: str
    status: str  # 'success' | 'failed' | 'skipped'
    attempts: int
    sent_count: int
    skipped_count: int
    errors_count: int
    entries: list[SyncEntry]
    synced_at: str
    last_error: str | None


async def _build_entries(
    db: AsyncSession, exam_id: int
) -> tuple[list[SyncEntry], int, int]:
    """Submit/graded urinishlarni yig'ib SyncEntry ro'yxati qaytaradi."""
    valid_statuses = ("submitted", "auto_submitted", "graded")
    stmt = (
        select(ExamAttempt, User)
        .join(User, User.id == ExamAttempt.user_id)
        .where(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.status.in_(valid_statuses),
        )
        .options(selectinload(ExamAttempt.answers))
    )
    rows = (await db.execute(stmt)).all()

    entries: list[SyncEntry] = []
    sent = 0
    skipped = 0

    for attempt, user in rows:
        pinfl: str | None = getattr(user, "pinfl", None) or getattr(
            getattr(user, "profile", None), "pinfl", None
        )
        if pinfl is None:
            skipped += 1
            logger.warning(
                "hemis_sync.skipped_no_pinfl exam=%s user=%s", exam_id, user.id
            )
        else:
            sent += 1
        entries.append(
            {
                "student_user_id": user.id,
                "student_pinfl": pinfl,
                "score": str(attempt.total_score) if attempt.total_score else "0",
                "percentage": str(attempt.percentage) if attempt.percentage else "0",
                "status": attempt.status,
                "completed_at": (
                    attempt.submitted_at.isoformat()
                    if attempt.submitted_at
                    else None
                ),
            }
        )

    return entries, sent, skipped


async def send_exam_grades(db: AsyncSession, exam_id: int) -> SyncResult:
    """DAK exam baholarini HEMIS'ga yuborish.

    - Faqat `type='dak'` exam'lar uchun (boshqalarda ConflictError)
    - Har urinish `hemis_sync_log` jadvalga yoziladi
    - `HEMIS_SYNC_ENABLED=False` bo'lsa — `skipped` statusi bilan log yoziladi
    - 3 marta urinib ko'riladi (exponential backoff 0s/1s/3s)
    """
    exam = (
        await db.execute(
            select(Exam).where(Exam.id == exam_id, Exam.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if exam is None:
        raise NotFoundError("Imtihon topilmadi")

    if exam.type != "dak":
        raise ConflictError(
            "HEMIS sync faqat DAK (Davlat attestatsiya komissiyasi) imtihonlari uchun"
        )

    entries, sent, skipped = await _build_entries(db, exam_id)

    payload = {
        "exam_id": exam_id,
        "exam_type": exam.type,
        "title": exam.title,
        "completed_at": (
            exam.closed_at.isoformat() if exam.closed_at else datetime.now(UTC).isoformat()
        ),
        "entries": [
            {
                "pinfl": e["student_pinfl"],
                "score": e["score"],
                "percentage": e["percentage"],
                "status": e["status"],
                "completed_at": e["completed_at"],
            }
            for e in entries
            if e["student_pinfl"]
        ],
    }

    # Sync log row
    log_row = HemisSyncLog(
        sync_type="exam_grades",
        target_id=exam_id,
        status="pending",
        attempts=0,
        payload=payload,
    )
    db.add(log_row)
    await db.flush()

    if not settings.HEMIS_SYNC_ENABLED:
        log_row.status = "skipped"
        log_row.last_error = "HEMIS_SYNC_ENABLED=False"
        log_row.completed_at = datetime.now(UTC)
        await db.flush()
        return {
            "log_id": log_row.id,
            "exam_id": exam_id,
            "exam_type": exam.type,
            "status": "skipped",
            "attempts": 0,
            "sent_count": sent,
            "skipped_count": skipped,
            "errors_count": 0,
            "entries": entries,
            "synced_at": log_row.completed_at.isoformat(),
            "last_error": "sync disabled (dev mode)",
        }

    log_row.status = "retrying"
    await db.flush()

    last_error: str | None = None
    attempt_count = 0

    async def _do_push() -> dict:
        nonlocal attempt_count
        attempt_count += 1
        async with HemisClient() as client:
            return await client.push_exam_grades(payload=payload)

    try:
        response = await retry_async(
            _do_push,
            attempts=3,
            backoff_seconds=(0.0, 1.0, 3.0),
            retry_on=(HemisError,),
            label=f"exam_grades_{exam_id}",
        )
        log_row.status = "success"
        log_row.response = response
        log_row.attempts = attempt_count
        log_row.completed_at = datetime.now(UTC)
    except HemisError as e:
        last_error = str(e)
        log_row.status = "failed"
        log_row.last_error = last_error
        log_row.attempts = attempt_count
        logger.exception("hemis_sync.failed exam=%s", exam_id)

    await db.flush()

    return {
        "log_id": log_row.id,
        "exam_id": exam_id,
        "exam_type": exam.type,
        "status": log_row.status,
        "attempts": log_row.attempts,
        "sent_count": sent,
        "skipped_count": skipped,
        "errors_count": 0 if log_row.status == "success" else 1,
        "entries": entries,
        "synced_at": (
            log_row.completed_at.isoformat()
            if log_row.completed_at
            else datetime.now(UTC).isoformat()
        ),
        "last_error": last_error,
    }


async def list_sync_logs(
    db: AsyncSession,
    *,
    sync_type: str | None = None,
    status: str | None = None,
    target_id: int | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[HemisSyncLog], int]:
    """Admin uchun: HEMIS sinxronizatsiya audit logini ko'rish."""
    from sqlalchemy import func

    stmt = select(HemisSyncLog)
    if sync_type:
        stmt = stmt.where(HemisSyncLog.sync_type == sync_type)
    if status:
        stmt = stmt.where(HemisSyncLog.status == status)
    if target_id is not None:
        stmt = stmt.where(HemisSyncLog.target_id == target_id)

    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()

    stmt = (
        stmt.order_by(HemisSyncLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await db.execute(stmt)).scalars().all()
    return list(items), int(total)


async def retry_failed_log(db: AsyncSession, log_id: int) -> SyncResult:
    """Failed sync log'ni qayta urinish (target_id bo'yicha yangi sync)."""
    log = (
        await db.execute(
            select(HemisSyncLog).where(HemisSyncLog.id == log_id)
        )
    ).scalar_one_or_none()
    if log is None:
        raise NotFoundError("Sync log topilmadi")
    if log.status == "success":
        raise ConflictError("Bu sync allaqachon muvaffaqiyatli")
    if log.sync_type != "exam_grades":
        raise ConflictError("Faqat exam_grades retry qilinadi")
    if log.target_id is None:
        raise ConflictError("Target ID yo'q")
    return await send_exam_grades(db, log.target_id)

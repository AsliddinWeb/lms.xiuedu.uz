"""Notification service — Phase 7d.

Bildirishnomalarni yaratish, ko'rsatish, o'qildi deb belgilash. Asosiy
trigger funksiyalari notify_* prefiks bilan — boshqa modullardan chaqiriladi.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import Notification


def _now() -> datetime:
    return datetime.now(UTC)


async def create_for_user(
    db: AsyncSession,
    *,
    user_id: int,
    event_type: str,
    title: str,
    body: str | None = None,
    action_url: str | None = None,
    data: dict[str, Any] | None = None,
) -> Notification:
    n = Notification(
        user_id=user_id,
        event_type=event_type,
        title=title,
        body=body,
        action_url=action_url,
        data=data,
    )
    db.add(n)
    await db.flush()
    return n


async def create_for_users(
    db: AsyncSession,
    *,
    user_ids: list[int],
    event_type: str,
    title: str,
    body: str | None = None,
    action_url: str | None = None,
    data: dict[str, Any] | None = None,
) -> int:
    """Bir nechta foydalanuvchiga bir xil bildirishnoma — fan-out."""
    if not user_ids:
        return 0
    rows = [
        Notification(
            user_id=uid,
            event_type=event_type,
            title=title,
            body=body,
            action_url=action_url,
            data=data,
        )
        for uid in user_ids
    ]
    db.add_all(rows)
    await db.flush()
    return len(rows)


async def list_for_user(
    db: AsyncSession,
    user_id: int,
    *,
    unread_only: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Notification], int]:
    stmt = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))

    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()

    stmt = (
        stmt.order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await db.execute(stmt)).scalars().all()
    return list(items), int(total)


async def count_unread(db: AsyncSession, user_id: int) -> int:
    count = (
        await db.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
        )
    ).scalar_one()
    return int(count)


async def mark_read(
    db: AsyncSession, notification_id: int, user_id: int
) -> Notification | None:
    n = (
        await db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if n is None:
        return None
    if n.read_at is None:
        n.read_at = _now()
        await db.flush()
    return n


async def mark_all_read(db: AsyncSession, user_id: int) -> int:
    res = await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        .values(read_at=_now())
    )
    await db.flush()
    return int(res.rowcount or 0)


# ============================================================================
# Event triggers — boshqa modullardan chaqiriladi
# ============================================================================


async def notify_exam_published(
    db: AsyncSession, *, exam_id: int, exam_title: str, course_id: int
) -> int:
    """Kurs ga yozilgan barcha talabalarga bildirishnoma."""
    from app.modules.courses.models import Enrollment

    student_ids = (
        await db.execute(
            select(Enrollment.user_id).where(Enrollment.course_id == course_id)
        )
    ).scalars().all()
    return await create_for_users(
        db,
        user_ids=list(student_ids),
        event_type="exam.published",
        title=f"Yangi imtihon: {exam_title}",
        body="Imtihon ochildi — boshlash uchun lobby sahifasini oching.",
        action_url=f"/app/exams/{exam_id}/lobby",
        data={"exam_id": exam_id, "course_id": course_id},
    )


async def notify_attempt_graded(
    db: AsyncSession, *, attempt_id: int, exam_id: int, user_id: int, percentage: str | float
) -> Notification:
    return await create_for_user(
        db,
        user_id=user_id,
        event_type="exam.graded",
        title="Imtihon natijasi tayyor",
        body=f"Foiz: {percentage}%",
        action_url=f"/app/exams/{exam_id}/result/{attempt_id}",
        data={"exam_id": exam_id, "attempt_id": attempt_id, "percentage": str(percentage)},
    )


async def notify_appeal_response(
    db: AsyncSession,
    *,
    appeal_id: int,
    user_id: int,
    decision: str,
    submission_id: int | None = None,
) -> Notification:
    # Talabada appeals detail sahifasi yo'q — submission'ga (assignment-detail) yoki
    # umumiy assignments ro'yxatiga yo'naltiramiz (Phase 13.19).
    action_url = (
        f"/app/assignments?submission_id={submission_id}"
        if submission_id is not None
        else "/app/assignments"
    )
    return await create_for_user(
        db,
        user_id=user_id,
        event_type="appeal.response",
        title="Apellyatsiyaga javob",
        body=f"Qaror: {decision}",
        action_url=action_url,
        data={"appeal_id": appeal_id, "submission_id": submission_id, "decision": decision},
    )


async def notify_certificate_issued(
    db: AsyncSession,
    *,
    user_id: int,
    certificate_id: int,
    certificate_number: str,
    course_title: str,
) -> Notification:
    """Sertifikat berilganda talaba'ga bildirishnoma (Phase 13.17)."""
    return await create_for_user(
        db,
        user_id=user_id,
        event_type="certificate.issued",
        title="Sertifikat berildi",
        body=f"{course_title} kursi uchun sertifikat tayyor: {certificate_number}",
        action_url="/app/certificates",
        data={
            "certificate_id": certificate_id,
            "certificate_number": certificate_number,
        },
    )


async def notify_badge_awarded(
    db: AsyncSession,
    *,
    user_id: int,
    badge_code: str,
    badge_title: str,
    points_reward: int,
) -> Notification:
    """Yangi nishon olingan paytda bildirishnoma (Phase 13.18)."""
    return await create_for_user(
        db,
        user_id=user_id,
        event_type="badge.awarded",
        title=f"Yangi nishon: {badge_title}",
        body=(
            f"+{points_reward} ball qo'shildi"
            if points_reward > 0
            else None
        ),
        action_url="/app/achievements",
        data={"badge_code": badge_code, "points_reward": points_reward},
    )


async def notify_new_chat_message(
    db: AsyncSession,
    *,
    conversation_id: int,
    sender_id: int,
    sender_name: str,
    body_preview: str | None,
    recipient_ids: list[int],
) -> int:
    """Chat xabaridan keyin offline a'zolarga bildirishnoma.

    Eslatma: a'zo online bo'lsa ham yaratiladi — push/bell uchun.
    Muted membership filtering xizmat darajasida hozircha qo'llanmaydi.
    """
    targets = [uid for uid in recipient_ids if uid != sender_id]
    if not targets:
        return 0
    preview = (body_preview or "").strip()
    if len(preview) > 140:
        preview = preview[:137] + "..."
    return await create_for_users(
        db,
        user_ids=targets,
        event_type="chat.message.new",
        title=f"Yangi xabar: {sender_name}",
        body=preview or None,
        action_url=f"/app/chat?c={conversation_id}",
        data={"conversation_id": conversation_id, "sender_id": sender_id},
    )


async def notify_forum_reply(
    db: AsyncSession,
    *,
    thread_id: int,
    thread_title: str,
    author_id: int,
    author_name: str,
    recipient_ids: list[int],
) -> int:
    """Mavzu muallifi va boshqa qatnashchilarga reply bildirishnomasi."""
    targets = [uid for uid in recipient_ids if uid != author_id]
    if not targets:
        return 0
    return await create_for_users(
        db,
        user_ids=targets,
        event_type="forum.reply",
        title=f"{author_name}: {thread_title}",
        body="Mavzuga yangi javob qo'shildi",
        action_url=f"/app/forum/threads/{thread_id}",
        data={"thread_id": thread_id, "author_id": author_id},
    )


async def notify_live_scheduled(
    db: AsyncSession,
    *,
    session_id: int,
    title: str,
    scheduled_start: str,
    course_id: int | None,
) -> int:
    """Kurs ga yozilgan talabalarga jonli dars haqida xabar (course_id berilsa)."""
    if course_id is None:
        return 0
    from app.modules.courses.models import Enrollment

    student_ids = (
        await db.execute(
            select(Enrollment.user_id).where(Enrollment.course_id == course_id)
        )
    ).scalars().all()
    return await create_for_users(
        db,
        user_ids=list(student_ids),
        event_type="live.scheduled",
        title=f"Yangi live dars: {title}",
        body=f"Boshlanish vaqti: {scheduled_start}",
        action_url=f"/app/live/{session_id}/lobby",
        data={"session_id": session_id, "course_id": course_id},
    )

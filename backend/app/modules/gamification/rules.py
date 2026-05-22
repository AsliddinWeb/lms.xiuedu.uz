"""Gamification qoidalari — Phase 11e.

Event turi → ball miqdori xaritasi va shu event natijasida tekshiriladigan
badge'lar.

Yangi qoida qo'shish uchun:
    1. `POINTS_TABLE` ga event_type qo'shing
    2. Tegishli badge'larni `BADGE_RULES` ichida code => async function bilan e'lon qiling
       Funksiya `(db, user_id, context) -> bool` qaytaradi — agar shart bajarilsa
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

# ============================================================================
# Ball xaritasi
# ============================================================================

POINTS_TABLE: dict[str, int] = {
    # Kurs
    "lesson.completed": 5,
    "course.completed": 100,
    # Imtihon
    "exam.passed": 50,
    "exam.perfect": 75,  # 100% bo'lganda qo'shimcha bonus
    # Topshiriq
    "assignment.submitted": 10,
    "assignment.graded_pass": 20,
    # Ijtimoiy faollik
    "comment.created": 2,
    "forum.thread.created": 5,
    "forum.post.created": 3,
    "forum.post.liked": 1,  # like olganda muallifga
    # Live
    "live.attended": 10,
    # Streak (kelajakda)
    "streak.day_7": 50,
    "streak.day_30": 200,
}


def points_for(event_type: str) -> int:
    return POINTS_TABLE.get(event_type, 0)


# ============================================================================
# Badge qoidalari — har bir event'dan keyin tekshiriladigan tasdiqlovchilar
# ============================================================================

BadgeChecker = Callable[[AsyncSession, int, dict[str, Any] | None], Awaitable[bool]]


async def _check_first_lesson(
    db: AsyncSession, user_id: int, context: dict[str, Any] | None
) -> bool:
    """Birinchi tugatilgan dars."""
    from app.modules.gamification.models import GamificationEvent

    count = (
        await db.execute(
            select(func.count(GamificationEvent.id)).where(
                GamificationEvent.user_id == user_id,
                GamificationEvent.event_type == "lesson.completed",
            )
        )
    ).scalar_one()
    return int(count) >= 1


async def _check_first_course(
    db: AsyncSession, user_id: int, context: dict[str, Any] | None
) -> bool:
    """Birinchi muvaffaqiyatli tugatilgan kurs."""
    from app.modules.gamification.models import GamificationEvent

    count = (
        await db.execute(
            select(func.count(GamificationEvent.id)).where(
                GamificationEvent.user_id == user_id,
                GamificationEvent.event_type == "course.completed",
            )
        )
    ).scalar_one()
    return int(count) >= 1


async def _check_course_master(
    db: AsyncSession, user_id: int, context: dict[str, Any] | None
) -> bool:
    """5 ta yoki undan ko'p kurs tugatgan."""
    from app.modules.gamification.models import GamificationEvent

    count = (
        await db.execute(
            select(func.count(GamificationEvent.id)).where(
                GamificationEvent.user_id == user_id,
                GamificationEvent.event_type == "course.completed",
            )
        )
    ).scalar_one()
    return int(count) >= 5


async def _check_exam_ace(
    db: AsyncSession, user_id: int, context: dict[str, Any] | None
) -> bool:
    """Birinchi marta 100% imtihon."""
    from app.modules.gamification.models import GamificationEvent

    count = (
        await db.execute(
            select(func.count(GamificationEvent.id)).where(
                GamificationEvent.user_id == user_id,
                GamificationEvent.event_type == "exam.perfect",
            )
        )
    ).scalar_one()
    return int(count) >= 1


async def _check_social_butterfly(
    db: AsyncSession, user_id: int, context: dict[str, Any] | None
) -> bool:
    """10 ta izoh yozgan."""
    from app.modules.gamification.models import GamificationEvent

    count = (
        await db.execute(
            select(func.count(GamificationEvent.id)).where(
                GamificationEvent.user_id == user_id,
                GamificationEvent.event_type == "comment.created",
            )
        )
    ).scalar_one()
    return int(count) >= 10


async def _check_helpful_voice(
    db: AsyncSession, user_id: int, context: dict[str, Any] | None
) -> bool:
    """Forum'da 10 ta like olgan."""
    from app.modules.gamification.models import GamificationEvent

    count = (
        await db.execute(
            select(func.count(GamificationEvent.id)).where(
                GamificationEvent.user_id == user_id,
                GamificationEvent.event_type == "forum.post.liked",
            )
        )
    ).scalar_one()
    return int(count) >= 10


# code -> checker
BADGE_RULES: dict[str, BadgeChecker] = {
    "first_lesson": _check_first_lesson,
    "first_course": _check_first_course,
    "course_master": _check_course_master,
    "exam_ace": _check_exam_ace,
    "social_butterfly": _check_social_butterfly,
    "helpful_voice": _check_helpful_voice,
}


# Event turi -> tekshirilishi mumkin bo'lgan badge code'lar (perf optimizatsiya).
# Bo'sh tuple => barcha checker'lar tekshiriladi (default).
EVENT_TO_BADGES: dict[str, tuple[str, ...]] = {
    "lesson.completed": ("first_lesson",),
    "course.completed": ("first_course", "course_master"),
    "exam.perfect": ("exam_ace",),
    "comment.created": ("social_butterfly",),
    "forum.post.liked": ("helpful_voice",),
}


def candidate_badges(event_type: str) -> tuple[str, ...]:
    return EVENT_TO_BADGES.get(event_type, ())

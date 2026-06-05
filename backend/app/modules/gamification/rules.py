"""Gamification qoidalari — Phase 11e (qayta ishlangan: yagona manba).

Har bir badge **bitta haqiqiy jarayonga** bog'langan: ma'lum event turi va shu
event sonining ostonasi (target). Shu tufayli nishon "sababsiz" emas — uni olish
uchun aniq nima qilish kerakligi (va qancha qolgani) progress orqali ko'rinadi.

Yangi qoida qo'shish: `POINTS_TABLE` ga ball, `BADGE_TARGETS` ga (event, target)
qo'shing — checker, candidate xaritasi va progress avtomatik hosil bo'ladi.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

# ============================================================================
# Ball xaritasi — har bir foydali harakat aniq ball beradi (sabab bilan)
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
# Badge qoidalari — har biri (metric event, target) ga bog'langan
# ============================================================================

# code -> (qaysi event sanaladi, nechta bo'lsa beriladi)
# Tartib muhim: bir event'ga bog'liq badge'lar past target -> yuqori target.
BADGE_TARGETS: dict[str, tuple[str, int]] = {
    "first_lesson": ("lesson.completed", 1),
    "first_course": ("course.completed", 1),
    "course_master": ("course.completed", 5),
    "exam_ace": ("exam.perfect", 1),
    "social_butterfly": ("comment.created", 10),
    "helpful_voice": ("forum.post.liked", 10),
}


def badge_metric(code: str) -> tuple[str, int] | None:
    """Badge'ning (metric event, target) juftligi — progress uchun."""
    return BADGE_TARGETS.get(code)


BadgeChecker = Callable[[AsyncSession, int, dict[str, Any] | None], Awaitable[bool]]


async def _count_events(db: AsyncSession, user_id: int, event_type: str) -> int:
    from app.modules.gamification.models import GamificationEvent

    return int(
        (
            await db.execute(
                select(func.count(GamificationEvent.id)).where(
                    GamificationEvent.user_id == user_id,
                    GamificationEvent.event_type == event_type,
                )
            )
        ).scalar_one()
    )


def _make_checker(event_type: str, target: int) -> BadgeChecker:
    """(event, target) -> 'shu event soni >= target' tekshiruvchisi."""

    async def _check(
        db: AsyncSession, user_id: int, context: dict[str, Any] | None
    ) -> bool:
        return await _count_events(db, user_id, event_type) >= target

    return _check


# code -> checker (yagona manba'dan avtomatik)
BADGE_RULES: dict[str, BadgeChecker] = {
    code: _make_checker(event_type, target)
    for code, (event_type, target) in BADGE_TARGETS.items()
}


# Event turi -> shu event'dan keyin tekshiriladigan badge code'lar.
# BADGE_TARGETS tartibini saqlab teskari xarita quramiz (perf optimizatsiya).
EVENT_TO_BADGES: dict[str, tuple[str, ...]] = {}
for _code, (_event_type, _target) in BADGE_TARGETS.items():
    EVENT_TO_BADGES[_event_type] = EVENT_TO_BADGES.get(_event_type, ()) + (_code,)


def candidate_badges(event_type: str) -> tuple[str, ...]:
    return EVENT_TO_BADGES.get(event_type, ())

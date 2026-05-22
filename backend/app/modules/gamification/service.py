"""Gamification servisi — Phase 11e.

Asosiy entrypoint — `award_event(...)`. Boshqa modullardan chaqiriladi:
    await award_event(
        db,
        user_id=...,
        event_type="course.completed",
        context={"course_id": 42},
        dedupe_key=f"course.completed:{user_id}:{course_id}",
    )

Funksiya:
    1. Dedupe — agar shu dedupe_key bilan event bor bo'lsa, no-op
    2. POINTS_TABLE dan ball miqdorini olib, GamificationEvent yozadi
    3. UserPoints'ni yangilaydi (insert yoki increment)
    4. Tegishli badge'larni tekshirib, agar shart bajarilsa, UserBadge qo'yadi

Idempotency: dedupe_key UNIQUE INDEX (partial, NULL emaslar uchun) bilan
ta'minlangan — race condition'da bittasi muvaffaqiyatli yozadi, qolganlari
IntegrityError olib, sukut bilan o'tib ketishadi.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.gamification.models import (
    Badge,
    GamificationEvent,
    UserBadge,
    UserPoints,
)
from app.modules.gamification.rules import (
    BADGE_RULES,
    candidate_badges,
    points_for,
)

logger = get_logger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


# ============================================================================
# Award event (entrypoint)
# ============================================================================


async def award_event(
    db: AsyncSession,
    *,
    user_id: int,
    event_type: str,
    context: dict[str, Any] | None = None,
    dedupe_key: str | None = None,
    override_points: int | None = None,
) -> GamificationEvent | None:
    """Yangi event yozadi, ball qo'shadi, badge tekshiradi.

    Dedupe bo'lsa None qaytaradi.
    """
    if dedupe_key is not None:
        existing = (
            await db.execute(
                select(GamificationEvent.id).where(
                    GamificationEvent.dedupe_key == dedupe_key
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return None

    points = override_points if override_points is not None else points_for(event_type)
    now = _now()
    event = GamificationEvent(
        user_id=user_id,
        event_type=event_type,
        points_awarded=points,
        dedupe_key=dedupe_key,
        context=context,
        created_at=now,
    )
    db.add(event)
    try:
        await db.flush()
    except IntegrityError:
        # Race condition — boshqa request shu dedupe_key bilan yozib ulgurgan
        await db.rollback()
        return None

    # Ball'larni update qilish
    await _add_points(db, user_id=user_id, delta=points)

    # Badge'larni tekshirish
    if points > 0 or candidate_badges(event_type):
        await _check_badges(db, user_id=user_id, event_type=event_type, context=context)

    return event


# ============================================================================
# Points helpers
# ============================================================================


async def _add_points(db: AsyncSession, *, user_id: int, delta: int) -> None:
    if delta == 0:
        return
    up = await db.get(UserPoints, user_id)
    now = _now()
    if up is None:
        up = UserPoints(
            user_id=user_id,
            total_points=delta,
            weekly_points=delta,
            monthly_points=delta,
            weekly_reset_at=now,
            monthly_reset_at=now,
            updated_at=now,
        )
        db.add(up)
    else:
        up.total_points += delta
        up.weekly_points += delta
        up.monthly_points += delta
        up.updated_at = now
    await db.flush()


async def get_points(db: AsyncSession, user_id: int) -> UserPoints | None:
    return await db.get(UserPoints, user_id)


# ============================================================================
# Badge logic
# ============================================================================


async def _check_badges(
    db: AsyncSession,
    *,
    user_id: int,
    event_type: str,
    context: dict[str, Any] | None,
) -> list[Badge]:
    """Event'dan keyin tegishli badge'larni tekshirib, beradi."""
    codes = candidate_badges(event_type)
    if not codes:
        return []

    # Faqat hali olinmagan badge'larni topish
    earned_codes = set(
        (
            await db.execute(
                select(Badge.code)
                .join(UserBadge, UserBadge.badge_id == Badge.id)
                .where(UserBadge.user_id == user_id, Badge.code.in_(codes))
            )
        )
        .scalars()
        .all()
    )

    newly_awarded: list[Badge] = []
    for code in codes:
        if code in earned_codes:
            continue
        checker = BADGE_RULES.get(code)
        if checker is None:
            continue
        try:
            ok = await checker(db, user_id, context)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "gamif.badge_check_failed",
                code=code,
                user_id=user_id,
                error=str(exc),
            )
            continue
        if not ok:
            continue

        badge = (
            await db.execute(
                select(Badge).where(Badge.code == code, Badge.is_active.is_(True))
            )
        ).scalar_one_or_none()
        if badge is None:
            continue

        awarded = UserBadge(
            user_id=user_id,
            badge_id=badge.id,
            awarded_at=_now(),
            context=context,
        )
        db.add(awarded)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            continue

        if badge.points_reward > 0:
            await _add_points(db, user_id=user_id, delta=badge.points_reward)
        newly_awarded.append(badge)

        # Phase 13.18 — bildirishnoma (xato bo'lsa yutamiz, badge baribir saqlanadi)
        try:
            from app.modules.notifications import service as notifications_service

            await notifications_service.notify_badge_awarded(
                db,
                user_id=user_id,
                badge_code=badge.code,
                badge_title=badge.title,
                points_reward=badge.points_reward,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "gamif.notify_failed",
                code=badge.code,
                user_id=user_id,
                error=str(exc),
            )

    return newly_awarded


# ============================================================================
# Read API
# ============================================================================


async def list_user_badges(
    db: AsyncSession, user_id: int
) -> list[tuple[Badge, UserBadge]]:
    rows = (
        await db.execute(
            select(Badge, UserBadge)
            .join(UserBadge, UserBadge.badge_id == Badge.id)
            .where(UserBadge.user_id == user_id)
            .order_by(UserBadge.awarded_at.desc())
        )
    ).all()
    return [(b, ub) for b, ub in rows]


async def list_all_active_badges(db: AsyncSession) -> list[Badge]:
    rows = (
        await db.execute(
            select(Badge)
            .where(Badge.is_active.is_(True), Badge.is_hidden.is_(False))
            .order_by(Badge.category, Badge.id)
        )
    ).scalars().all()
    return list(rows)


async def leaderboard(
    db: AsyncSession,
    *,
    scope: str = "total",
    limit: int = 20,
) -> list[UserPoints]:
    """Top-N user'larni qaytaradi.

    scope: 'total' (default) | 'weekly' | 'monthly'
    """
    col = {
        "total": UserPoints.total_points,
        "weekly": UserPoints.weekly_points,
        "monthly": UserPoints.monthly_points,
    }.get(scope, UserPoints.total_points)

    stmt = (
        select(UserPoints)
        .where(col > 0)
        .order_by(desc(col))
        .limit(min(limit, 100))
    )
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows)


async def get_rank(
    db: AsyncSession, user_id: int, *, scope: str = "total"
) -> int | None:
    """User'ning leaderboarddagi o'rni (1-based). Ball 0 bo'lsa None."""
    col = {
        "total": UserPoints.total_points,
        "weekly": UserPoints.weekly_points,
        "monthly": UserPoints.monthly_points,
    }.get(scope, UserPoints.total_points)

    me = await db.get(UserPoints, user_id)
    if me is None:
        return None
    my_pts = getattr(me, col.key)  # type: ignore[attr-defined]
    if my_pts == 0:
        return None
    higher = (
        await db.execute(
            select(func.count()).select_from(
                select(UserPoints).where(col > my_pts).subquery()
            )
        )
    ).scalar_one()
    return int(higher) + 1

"""Gamification endpointlari — Phase 11e.

Routes:
    GET    /me/gamification               — talaba shaxsiy stat (ball + rank + recent badges)
    GET    /me/gamification/badges        — talabaning barcha nishonlari
    GET    /gamification/badges           — barcha mavjud badge katalogi (yashirin emas)
    GET    /gamification/leaderboard      — top-N reyting (scope=total|weekly|monthly)
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.modules.auth.dependencies import CurrentUser, DbSession
from app.modules.gamification import service as gamif_service
from app.modules.gamification.rules import badge_metric
from app.modules.gamification.schemas import (
    BadgeProgressItem,
    BadgePublic,
    LeaderboardItem,
    LeaderboardResponse,
    MyGamificationStats,
    UserBadgeItem,
)
from app.modules.users.models import User

router = APIRouter()


# ============================================================================
# My stats
# ============================================================================


@router.get(
    "/me/gamification",
    response_model=MyGamificationStats,
    tags=["gamification"],
)
async def my_gamification_stats(
    db: DbSession, user: CurrentUser
) -> MyGamificationStats:
    points = await gamif_service.get_points(db, user.id)
    badges_list = await gamif_service.list_user_badges(db, user.id)

    rank_total = await gamif_service.get_rank(db, user.id, scope="total")
    rank_weekly = await gamif_service.get_rank(db, user.id, scope="weekly")

    recent = [
        UserBadgeItem(
            badge=BadgePublic.model_validate(b),
            awarded_at=ub.awarded_at,
            context=ub.context,
        )
        for b, ub in badges_list[:5]
    ]

    return MyGamificationStats(
        total_points=points.total_points if points else 0,
        weekly_points=points.weekly_points if points else 0,
        monthly_points=points.monthly_points if points else 0,
        rank_total=rank_total,
        rank_weekly=rank_weekly,
        badges_count=len(badges_list),
        recent_badges=recent,
    )


@router.get(
    "/me/gamification/badges",
    response_model=list[UserBadgeItem],
    tags=["gamification"],
)
async def my_badges(
    db: DbSession, user: CurrentUser
) -> list[UserBadgeItem]:
    rows = await gamif_service.list_user_badges(db, user.id)
    return [
        UserBadgeItem(
            badge=BadgePublic.model_validate(b),
            awarded_at=ub.awarded_at,
            context=ub.context,
        )
        for b, ub in rows
    ]


@router.get(
    "/me/gamification/progress",
    response_model=list[BadgeProgressItem],
    tags=["gamification"],
)
async def my_badge_progress(
    db: DbSession, user: CurrentUser
) -> list[BadgeProgressItem]:
    """Har bir nishon + progress (current/target) + olingan bo'lsa sabab.

    Olingan nishonlar oldinda (sana bo'yicha), so'ng olinmaganlar maqsadga
    yaqinligi bo'yicha — talaba nimaga qancha qolganini ko'radi.
    """
    catalog = await gamif_service.list_all_active_badges(db)
    earned_rows = await gamif_service.list_user_badges(db, user.id)
    earned_map = {b.id: ub for b, ub in earned_rows}
    counts = await gamif_service.event_counts(db, user.id)

    items: list[BadgeProgressItem] = []
    for badge in catalog:
        metric = badge_metric(badge.code)
        event_type, target = metric if metric else ("", 1)
        cur_raw = counts.get(event_type, 0)
        ub = earned_map.get(badge.id)
        earned = ub is not None
        reason = None
        if earned:
            current = target
            reason = await gamif_service.earned_reason(db, badge.code, ub.context)
        else:
            current = min(cur_raw, target)
        items.append(
            BadgeProgressItem(
                badge=BadgePublic.model_validate(badge),
                earned=earned,
                awarded_at=ub.awarded_at if ub else None,
                current=current,
                target=target,
                reason=reason,
            )
        )

    items.sort(
        key=lambda it: (
            0 if it.earned else 1,
            -(it.awarded_at.timestamp()) if it.earned and it.awarded_at else 0,
            -(it.current / it.target) if it.target else 0,
        )
    )
    return items


# ============================================================================
# Public catalog
# ============================================================================


@router.get(
    "/gamification/badges",
    response_model=list[BadgePublic],
    tags=["gamification"],
)
async def list_badge_catalog(db: DbSession) -> list[BadgePublic]:
    rows = await gamif_service.list_all_active_badges(db)
    return [BadgePublic.model_validate(b) for b in rows]


# ============================================================================
# Leaderboard
# ============================================================================


@router.get(
    "/gamification/leaderboard",
    response_model=LeaderboardResponse,
    tags=["gamification"],
)
async def leaderboard(
    db: DbSession,
    user: CurrentUser,
    scope: Literal["total", "weekly", "monthly"] = Query(default="total"),
    limit: int = Query(default=20, ge=1, le=100),
) -> LeaderboardResponse:
    rows = await gamif_service.leaderboard(db, scope=scope, limit=limit)
    if not rows:
        return LeaderboardResponse(scope=scope, items=[], me_rank=None, me_points=None)

    user_ids = [r.user_id for r in rows]
    users_map = {
        u.id: u
        for u in (
            await db.execute(select(User).where(User.id.in_(user_ids)))
        )
        .scalars()
        .all()
    }

    col_attr = {
        "total": "total_points",
        "weekly": "weekly_points",
        "monthly": "monthly_points",
    }[scope]

    items: list[LeaderboardItem] = []
    for idx, row in enumerate(rows, start=1):
        u = users_map.get(row.user_id)
        items.append(
            LeaderboardItem(
                user_id=row.user_id,
                full_name=u.full_name if u else f"user#{row.user_id}",
                avatar_url=u.avatar_url if u else None,
                points=getattr(row, col_attr),
                rank=idx,
            )
        )

    me_points_row = await gamif_service.get_points(db, user.id)
    me_points = (
        getattr(me_points_row, col_attr) if me_points_row else 0
    )
    me_rank = await gamif_service.get_rank(db, user.id, scope=scope)
    return LeaderboardResponse(
        scope=scope, items=items, me_rank=me_rank, me_points=me_points
    )

"""Gamification Pydantic sxemalari — Phase 11e."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class BadgePublic(BaseModel):
    id: int
    code: str
    title: str
    description: str | None
    category: str
    icon_url: str | None
    points_reward: int
    is_hidden: bool

    model_config = ConfigDict(from_attributes=True)


class UserBadgeItem(BaseModel):
    badge: BadgePublic
    awarded_at: datetime
    context: dict[str, Any] | None


class MyGamificationStats(BaseModel):
    total_points: int
    weekly_points: int
    monthly_points: int
    rank_total: int | None
    rank_weekly: int | None
    badges_count: int
    recent_badges: list[UserBadgeItem]


class LeaderboardItem(BaseModel):
    user_id: int
    full_name: str
    avatar_url: str | None
    points: int
    rank: int


class LeaderboardResponse(BaseModel):
    scope: Literal["total", "weekly", "monthly"]
    items: list[LeaderboardItem]
    me_rank: int | None
    me_points: int | None

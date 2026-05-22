"""Gamification modellari — Phase 11e."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IDMixin


class Badge(Base, IDMixin):
    """Nishon katalogi. `code` orqali kodda award qilinadi."""

    __tablename__ = "badges"

    code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(
        String(40), nullable=False, default="achievement"
    )
    icon_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    points_reward: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Badge id={self.id} code={self.code!r}>"


class UserBadge(Base):
    """Foydalanuvchi - nishon junction."""

    __tablename__ = "user_badges"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    badge_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("badges.id", ondelete="CASCADE"),
        primary_key=True,
    )
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    context: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<UserBadge user={self.user_id} badge={self.badge_id}>"


class UserPoints(Base):
    """User'ning jami balli — leaderboard uchun denormallashtirilgan cache."""

    __tablename__ = "user_points"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    total_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    weekly_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    monthly_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    weekly_reset_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    monthly_reset_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def __repr__(self) -> str:
        return f"<UserPoints user={self.user_id} total={self.total_points}>"


class GamificationEvent(Base, IDMixin):
    """Xom event log — audit + qayta hisoblash imkoniyati."""

    __tablename__ = "gamification_events"
    __table_args__ = (
        Index(
            "ix_gamif_events_user_created",
            "user_id",
            text("created_at DESC"),
        ),
        Index(
            "ix_gamif_events_dedupe",
            "dedupe_key",
            unique=True,
            postgresql_where=text("dedupe_key IS NOT NULL"),
        ),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    points_awarded: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    dedupe_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    context: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<GamifEvent id={self.id} user={self.user_id} "
            f"type={self.event_type} pts={self.points_awarded}>"
        )

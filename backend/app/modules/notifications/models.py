"""Notification model — Phase 7d."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IDMixin, TimestampMixin


class Notification(Base, IDMixin, TimestampMixin):
    """Foydalanuvchiga yo'naltirilgan bitta bildirishnoma.

    `event_type` qiymatlari ([modules/notifications/__init__.py] ga qarang):
        'exam.published', 'exam.graded', 'appeal.response',
        'live.scheduled', 'live.starting', 'system'

    `read_at` — talaba/pedagog o'qib chiqqan vaqt (NULL = unread).
    `data` — strukturalangan kontekst (e.g. exam_id, attempt_id) — frontend
              tugmasi shundan URL quradi.
    """

    __tablename__ = "notifications"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    __table_args__ = (
        # Phase 8c — Bell polling: faqat unread, eng yangidan.
        # Partial index — read_at IS NULL bo'lgan qatorlar uchun.
        Index(
            "ix_notifications_user_unread",
            "user_id",
            "created_at",
            postgresql_where=text("read_at IS NULL"),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Notification id={self.id} user={self.user_id} "
            f"type={self.event_type} read={self.read_at is not None}>"
        )

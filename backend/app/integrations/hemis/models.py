"""HEMIS sync audit log — Phase 7c.

HEMIS bilan har sinxronizatsiya urinishi shu jadvalga yoziladi (success yoki failure).
Admin sahifasidan ko'rib chiqish + qayta urinish uchun.

Sync turlari:
    'exam_grades'   — DAK imtihon baholarini HEMIS'ga yuborish
    'schedule_pull' — HEMIS'dan dars jadvalini olib kelish (kelajak)
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IDMixin, TimestampMixin


class HemisSyncLog(Base, IDMixin, TimestampMixin):
    """HEMIS sinxronizatsiya audit yozuvi.

    `status` qiymatlari:
        'pending'   — yangi yaratilgan, hali urinilmagan
        'retrying'  — xatolik yuz berdi, qayta urinilmoqda
        'success'   — muvaffaqiyatli yuborildi
        'failed'    — barcha urinishlar tugadi
        'skipped'   — dry-run yoki disabled
    """

    __tablename__ = "hemis_sync_log"

    sync_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    target_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, index=True
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<HemisSyncLog id={self.id} type={self.sync_type} "
            f"target={self.target_id} status={self.status} att={self.attempts}>"
        )

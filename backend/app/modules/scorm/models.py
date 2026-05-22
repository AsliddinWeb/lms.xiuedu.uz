"""SCORM models — Phase 11a."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IDMixin, TimestampMixin


class ScormPackage(Base, IDMixin, TimestampMixin):
    """SCORM ZIP paket — `content_item` bilan 1:1 bog'liq.

    SCORM versiyalar:
        - '1.2'  — SCORM 1.2 (eski, eng ko'p tarqalgan)
        - '2004' — SCORM 2004 (yangiroq, sequencing/branching)
    """

    __tablename__ = "scorm_packages"

    content_item_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("content_items.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    version: Mapped[str] = mapped_column(String(10), nullable=False)
    manifest_identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Boshlovchi sahifa (iframe src), e.g. 'shared/launchpage.html'
    launch_url: Mapped[str] = mapped_column(String(500), nullable=False)
    # MinIO bucket'dagi root prefix, e.g. 'scorm/{id}/'
    package_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    mastery_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    attempts: Mapped[list["ScormAttempt"]] = relationship(
        "ScormAttempt", back_populates="package", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ScormPackage id={self.id} version={self.version} launch={self.launch_url}>"


class ScormAttempt(Base, IDMixin, TimestampMixin):
    """SCORM sessiya — talaba paket bo'yicha urinish.

    Har user × package × attempt_number unique. Bir nechta urinish ruxsat
    etilgan (lekin odatda LMS faqat 1 ta attempt'ni ko'rsatadi va resume qilish
    mexanizmi orqali davom etadi).

    CMI data SCORM 1.2 model uchun:
        cmi.core.lesson_status, cmi.core.score.raw, cmi.suspend_data, ...
    SCORM 2004 model uchun:
        cmi.completion_status, cmi.score.scaled, cmi.suspend_data, ...
    """

    __tablename__ = "scorm_attempts"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "package_id",
            "attempt_number",
            name="uq_scorm_attempt_user_package_number",
        ),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    package_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("scorm_packages.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    lesson_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("lessons.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # 'in_progress' | 'completed' | 'passed' | 'failed' | 'incomplete' | 'browsed'
    status: Mapped[str] = mapped_column(
        String(30), default="in_progress", nullable=False
    )
    cmi_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    score_raw: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    score_min: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    score_max: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    # SCORM format: hh:mm:ss.ss (e.g. "01:23:45.50")
    total_time: Mapped[str | None] = mapped_column(String(20), nullable=True)
    session_time: Mapped[str | None] = mapped_column(String(20), nullable=True)
    bookmark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    suspend_data: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    package: Mapped[ScormPackage] = relationship(
        "ScormPackage", back_populates="attempts"
    )

    def __repr__(self) -> str:
        return (
            f"<ScormAttempt id={self.id} user={self.user_id} "
            f"package={self.package_id} #{self.attempt_number} {self.status}>"
        )

"""Live darslar moduli — Phase 5a (Backend models + scheduling).

Spec: docs/03-modules/08-live-classes.md (TZ).

Tuzilma:
    LiveSession (course_id/lesson_id, scheduled_*, provider, status, host)
      └── LiveAttendance (session_id, user_id) — har talaba uchun bitta
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IDMixin, TimestampMixin


class LiveSession(Base, IDMixin, TimestampMixin):
    """Real vaqtdagi audio/video dars."""

    __tablename__ = "live_sessions"

    organization_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    course_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    lesson_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("lessons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    scheduled_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    scheduled_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

    # 'native' — yagona qo'llab-quvvatlanadigan provider (LiveKit self-hosted, Phase 5)
    provider: Mapped[str] = mapped_column(
        String(20), default="native", nullable=False
    )
    provider_meeting_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    provider_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    host_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # 'scheduled' | 'live' | 'ended' | 'cancelled'
    status: Mapped[str] = mapped_column(
        String(20), default="scheduled", nullable=False, index=True
    )
    actual_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Recording (Phase 5d)
    is_recording_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    recording_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    recording_size_bytes: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    recording_duration_seconds: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    recording_mime_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    # Davomat (75% qoidasi) — 5e da to'liq qilinadi
    min_attendance_percent: Mapped[int] = mapped_column(
        Integer, default=75, nullable=False
    )

    # Waiting room — yoqilsa, host tasdiqlamaguncha talaba xonaga kira olmaydi
    requires_approval: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    attendances: Mapped[list["LiveAttendance"]] = relationship(
        "LiveAttendance",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    recordings: Mapped[list["LiveRecording"]] = relationship(
        "LiveRecording",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="LiveRecording.started_at.desc()",
    )

    def __repr__(self) -> str:
        return (
            f"<LiveSession id={self.id} title={self.title!r} "
            f"status={self.status} provider={self.provider}>"
        )


class LiveAttendance(Base, IDMixin):
    """Talabaning live sessionga davomatchi (UNIQUE session_id+user_id)."""

    __tablename__ = "live_attendance"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "user_id", name="uq_live_attendance_session_user"
        ),
    )

    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("live_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    joined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    left_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_counted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    session: Mapped[LiveSession] = relationship(
        "LiveSession", back_populates="attendances"
    )

    def __repr__(self) -> str:
        return (
            f"<LiveAttendance session={self.session_id} user={self.user_id} "
            f"min={self.total_minutes} counted={self.is_counted}>"
        )


class LiveAdmission(Base, IDMixin):
    """Waiting room — talaba xonaga kirish so'rovi (pending/approved/denied).

    `requires_approval` yoqilgan sessiyada talaba join-info so'raganda 'pending'
    yoziladi; host tasdiqlasa 'approved' (token beriladi), rad etsa 'denied'.
    """

    __tablename__ = "live_admissions"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "user_id", name="uq_live_admission_session_user"
        ),
    )

    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("live_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # pending | approved | denied
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<LiveAdmission session={self.session_id} user={self.user_id} "
            f"status={self.status}>"
        )


class LiveRecording(Base, IDMixin, TimestampMixin):
    """Live dars yozuvi — Phase 7a.

    Bitta sessiya bir nechta yozuvga ega bo'lishi mumkin (pedagog REC tugmasini
    bir necha marta bosishi). Yozuv pedagog brauzeridagi MediaRecorder orqali
    olinadi, MinIO'ga blob sifatida yuklanadi.

    `status` qiymatlari:
        'recording'  — boshlangan, hali tugamagan (faqat in-memory)
        'finalized'  — yuklangan va metadata yozilgan
        'failed'     — yuklash xato bilan tugadi
    """

    __tablename__ = "live_recordings"

    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("live_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recorded_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), default="recording", nullable=False, index=True
    )
    object_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str] = mapped_column(String(60), nullable=False, default="video/webm")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finalized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    session: Mapped[LiveSession] = relationship(
        "LiveSession", back_populates="recordings"
    )

    def __repr__(self) -> str:
        return (
            f"<LiveRecording id={self.id} session={self.session_id} "
            f"status={self.status} dur={self.duration_seconds}>"
        )


class LiveCaption(Base, IDMixin, TimestampMixin):
    """Live dars uchun real-time caption (Phase 9c).

    Web Speech API yoki Whisper'dan kelgan transcript bo'lagi. Pedagog speech
    recognition orqali tanilgan matn batch'lar bilan yuboriladi (har 5s).

    `lang` ISO-639 (uz, uz-cyr, ru, en).
    """

    __tablename__ = "live_captions"

    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("live_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    speaker_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    start_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    end_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    lang: Mapped[str] = mapped_column(String(10), nullable=False, default="uz")

    def __repr__(self) -> str:
        return (
            f"<LiveCaption id={self.id} session={self.session_id} "
            f"{self.start_ms}-{self.end_ms}ms lang={self.lang}>"
        )

"""Assignments moduli — Phase 4a + 4b.

Spec: docs/03-modules/07-assignments.md (MVP scope: essay + file).

Tuzilma:
    Course → Assignment (lesson_id ixtiyoriy, rubric_id ixtiyoriy)
    Assignment → Submission (UNIQUE per assignment+user+attempt_number)
    Rubric (qayta ishlatiluvchi baholash mezonlari)

Phase 4a scope:
    - 'essay'  — matnli javob (content)
    - 'file'   — fayl yuklash (files JSONB array)
    - Status workflow: submitted → grading

Phase 4b da qo'shiladi:
    - Rubric (kriteriyali baholash)
    - rubric_scores + annotations (Submission ichida JSONB)
    - grade_letter (A/B/C/D/F)
    - final_score = score × (1 - days_late × late_penalty/100), 0 dan past tushmaydi
    - Status workflow kengaytirildi: graded / returned

Phase 4e va keyingi sub-fazalarga qoldirilgan:
    - Plagiat tekshiruvi (Antiplag)
    - Peer review
    - Apellyatsiya
    - Quiz / Code (Phase 6 imtihonlar bilan birga)
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IDMixin, SoftDeleteMixin, TimestampMixin


class Rubric(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Qayta ishlatiluvchi baholash mezonlari (Phase 4b).

    `criteria` JSONB sxemasi:
        [
          {
            "key": "structure",
            "name": "Tuzilish va mantiq",
            "max_points": 25,
            "levels": [
              {"label": "A'lo", "points": 25, "description": "..."},
              {"label": "Yaxshi", "points": 18, "description": "..."},
              {"label": "Kifoya", "points": 12, "description": "..."},
              {"label": "Past", "points": 5,  "description": "..."}
            ]
          },
          ...
        ]
    `total_points` — kriteriyalar `max_points` yig'indisi (validatsiya bilan).
    """

    __tablename__ = "rubrics"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_points: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), default=Decimal("100"), nullable=False
    )
    criteria: Mapped[list[dict]] = mapped_column(JSONB, default=list, nullable=False)

    organization_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<Rubric id={self.id} title={self.title!r}>"


class Assignment(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Topshiriq — kursga (va ixtiyoriy darsga) bog'langan."""

    __tablename__ = "assignments"

    course_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("courses.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    lesson_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("lessons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 'essay' | 'file' (Phase 4a MVP)
    type: Mapped[str] = mapped_column(String(30), nullable=False)

    available_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    max_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("100"), nullable=False
    )
    pass_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    weight_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    max_attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    late_submission_allowed: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    late_penalty_per_day: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0"), nullable=False
    )

    allowed_file_types: Mapped[list[str]] = mapped_column(
        ARRAY(String(20)), default=list, nullable=False
    )
    max_file_size_mb: Mapped[int] = mapped_column(Integer, default=50, nullable=False)

    is_published: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )

    # Phase 4b: ixtiyoriy rubric (kriteriyali baholash)
    rubric_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("rubrics.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Phase 4e: plagiat tekshiruvi
    plagiarism_check_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    plagiarism_threshold: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("30"), nullable=False
    )

    # Phase 4e: peer review
    peer_review_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    peer_reviews_per_submission: Mapped[int] = mapped_column(
        Integer, default=3, nullable=False
    )

    created_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    submissions: Mapped[list["Submission"]] = relationship(
        "Submission", back_populates="assignment", cascade="all, delete-orphan"
    )
    rubric: Mapped["Rubric | None"] = relationship(
        "Rubric",
        primaryjoin="Assignment.rubric_id == Rubric.id",
        foreign_keys=[rubric_id],
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<Assignment id={self.id} type={self.type} course_id={self.course_id}>"


class Submission(Base, IDMixin):
    """Talabaning topshirig'i — har attempt alohida qator."""

    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint(
            "assignment_id",
            "user_id",
            "attempt_number",
            name="uq_submission_assignment_user_attempt",
        ),
        # Phase 8c — talabaning topshiriqdagi urinishlari ro'yxati uchun.
        Index("ix_submissions_assignment_user", "assignment_id", "user_id"),
    )

    assignment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("assignments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    # files: list of {name, url, mime, size}
    files: Mapped[list[dict]] = mapped_column(JSONB, default=list, nullable=False)

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_late: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    days_late: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 'submitted' | 'grading' | 'graded' | 'returned'
    status: Mapped[str] = mapped_column(
        String(20), default="submitted", nullable=False, index=True
    )

    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    final_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    grade_letter: Mapped[str | None] = mapped_column(String(5), nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Phase 4b: rubric kriteriyalari bo'yicha {key: points} ko'rinishida
    # Misol: {"structure": 22, "grammar": 18, "argument": 24}
    rubric_scores: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # Inline annotations [{page, x, y, w, h, text, author_id, created_at}, ...]
    annotations: Mapped[list[dict]] = mapped_column(JSONB, default=list, nullable=False)

    # Phase 4e: plagiat
    plagiarism_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    plagiarism_report_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    plagiarism_flagged: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    plagiarism_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    graded_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    graded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    assignment: Mapped[Assignment] = relationship(
        "Assignment", back_populates="submissions"
    )

    def __repr__(self) -> str:
        return (
            f"<Submission id={self.id} assignment={self.assignment_id} "
            f"user={self.user_id} attempt={self.attempt_number} {self.status}>"
        )


class PeerReview(Base, IDMixin, TimestampMixin):
    """Peer review (Phase 4e) — anonim talabalar baholashi.

    Pedagog `POST /assignments/{id}/peer-review/start` chaqirganda har bitta
    submitted submission'ga `peer_reviews_per_submission` ta tasodifiy reviewer
    biriktiriladi (PeerReview ro'yxatlari yaratiladi, dastlab `submitted_at=NULL`).
    Talaba `submitted_at` qo'yilganda — review yakunlangan deb hisoblanadi.

    UNIQUE submission+reviewer — bir talaba bir submissionni faqat bir marta baholaydi.
    """

    __tablename__ = "peer_reviews"
    __table_args__ = (
        UniqueConstraint(
            "submission_id", "reviewer_id", name="uq_peer_review_sub_reviewer"
        ),
    )

    submission_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("submissions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    reviewer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    rubric_scores: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        done = self.submitted_at is not None
        return f"<PeerReview sub={self.submission_id} reviewer={self.reviewer_id} done={done}>"


class GradeAppeal(Base, IDMixin, TimestampMixin):
    """Apellyatsiya (Phase 4e) — talaba bahoga shikoyat.

    Status: 'pending' → 'approved' (yangi score qo'yiladi) yoki 'rejected'.
    """

    __tablename__ = "grade_appeals"

    submission_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("submissions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    student_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, index=True
    )
    new_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<GradeAppeal sub={self.submission_id} student={self.student_id} "
            f"{self.status}>"
        )

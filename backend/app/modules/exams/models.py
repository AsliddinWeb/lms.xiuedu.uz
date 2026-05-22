"""Exam SQLAlchemy modellari — Phase 6a.

Tuzilma:
    Course → Exam → Question → QuestionOption
    Exam ham `Lesson`'ga ixtiyoriy bog'lanadi (lesson-level quiz uchun).

Phase 6a scope:
    - Exam: imtihon (settings + proctoring config + schedule)
    - Question: turli savol turlari (single/multiple/true_false/short_text/essay/code/file_upload)
    - QuestionOption: single/multiple/true_false uchun variantlar

Phase 6b da qo'shiladi:
    - ExamAttempt: talaba urinishi (status + timing + scoring)
    - Answer: bir attempt ichidagi savol javobi

Phase 6f da qo'shiladi:
    - ProctoringSession + ProctoringEvent + Snapshot (avtoproctoring uchun)
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
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IDMixin, SoftDeleteMixin, TimestampMixin


class Exam(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Imtihon — kursga (va ixtiyoriy darsga) bog'langan.

    `type` qiymatlari:
        - 'midterm'  — oraliq nazorat
        - 'final'    — yakuniy nazorat
        - 'quiz'     — qisqa test (dars ichida)
        - 'dak'      — Davlat attestatsiya komissiyasi (HEMIS sync majburiy)

    `status` qiymatlari:
        - 'draft'      — yaratilmoqda
        - 'published'  — talabalarga ko'rinadi
        - 'archived'   — yopildi
    """

    __tablename__ = "exams"

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
    organization_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False, index=True
    )

    # Settings
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    passing_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("60"), nullable=False
    )
    shuffle_questions: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    shuffle_options: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_correct_answers: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    question_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Proctoring (559-qaror 10-band: majburiy)
    proctoring_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    require_face_id: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_screen_share: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    allow_tab_switch: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_face_loss_seconds: Mapped[int] = mapped_column(
        Integer, default=10, nullable=False
    )

    # Schedule
    available_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    available_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    questions: Mapped[list["Question"]] = relationship(
        "Question",
        back_populates="exam",
        cascade="all, delete-orphan",
        order_by="Question.order_index",
    )
    attempts: Mapped[list["ExamAttempt"]] = relationship(
        "ExamAttempt",
        back_populates="exam",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Exam id={self.id} title={self.title!r} status={self.status}>"


class Question(Base, IDMixin, TimestampMixin):
    """Imtihon savoli.

    `type` qiymatlari:
        - 'single_choice'    — bitta to'g'ri javob (radio)
        - 'multiple_choice'  — bir nechta to'g'ri javob (checkbox)
        - 'true_false'       — Ha/Yo'q
        - 'short_text'       — qisqa matn javob (exact/regex match)
        - 'essay'            — uzun matn (manual grading)
        - 'code'             — kod javob (Phase 9 da runner; hozir manual)
        - 'file_upload'      — fayl yuklash (manual)
    """

    __tablename__ = "exam_questions"

    exam_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    points: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("1.0"), nullable=False
    )
    required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Type-specific config
    code_language: Mapped[str | None] = mapped_column(String(20), nullable=True)
    code_initial: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_file_size_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    allowed_file_types: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(20)), nullable=True
    )

    # short_text auto-grading config
    exact_match: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    case_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    correct_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Muqobil javoblar JSON array sifatida: ["javob1", "Javob2", ...]
    alternative_answers: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    exam: Mapped["Exam"] = relationship("Exam", back_populates="questions")
    options: Mapped[list["QuestionOption"]] = relationship(
        "QuestionOption",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="QuestionOption.order_index",
    )

    def __repr__(self) -> str:
        return f"<Question id={self.id} type={self.type} order={self.order_index}>"


class QuestionOption(Base, IDMixin, TimestampMixin):
    """Single/Multiple/True-false savol varianti."""

    __tablename__ = "exam_question_options"

    question_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("exam_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    question: Mapped["Question"] = relationship("Question", back_populates="options")

    __table_args__ = (
        UniqueConstraint("question_id", "order_index", name="uq_question_option_order"),
    )

    def __repr__(self) -> str:
        return f"<QuestionOption id={self.id} q={self.question_id} correct={self.is_correct}>"


class ExamAttempt(Base, IDMixin, TimestampMixin):
    """Talaba imtihon urinishi.

    `status` qiymatlari:
        - 'in_progress'     — boshlangan, hali tugamagan
        - 'submitted'       — talaba submit qildi
        - 'auto_submitted'  — vaqt tugab, avtomatik submit qilindi
        - 'graded'          — pedagog manual baholashni tugatdi
        - 'flagged'         — proctoring/qoidabuzarlik tekshiruv kerak
        - 'invalidated'     — bekor qilindi (admin/pedagog)
    """

    __tablename__ = "exam_attempts"

    exam_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[str] = mapped_column(
        String(20), default="in_progress", nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deadline_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    time_spent_seconds: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    # Scoring
    auto_score: Mapped[Decimal | None] = mapped_column(
        Numeric(7, 2), nullable=True
    )
    manual_score: Mapped[Decimal | None] = mapped_column(
        Numeric(7, 2), nullable=True
    )
    total_score: Mapped[Decimal | None] = mapped_column(
        Numeric(7, 2), nullable=True
    )
    max_score: Mapped[Decimal | None] = mapped_column(
        Numeric(7, 2), nullable=True
    )
    percentage: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Randomization (bu attempt uchun savol/option tartibi)
    question_order: Mapped[list[int] | None] = mapped_column(JSONB, nullable=True)
    option_order: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Proctoring (Phase 6f'da to'liq ishlaydi)
    proctoring_session_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    violation_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Phase 9f — smart anomaly scoring
    smart_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    smart_flags: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    exam: Mapped["Exam"] = relationship("Exam", back_populates="attempts")
    answers: Mapped[list["Answer"]] = relationship(
        "Answer",
        back_populates="attempt",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "exam_id", "user_id", "attempt_number", name="uq_attempt_user_number"
        ),
        # Phase 8c — composite indices for hot filtr kombinatsiyalari
        Index("ix_exam_attempts_exam_user", "exam_id", "user_id"),
        Index("ix_exam_attempts_exam_status", "exam_id", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<ExamAttempt id={self.id} exam={self.exam_id} "
            f"user={self.user_id} #{self.attempt_number} {self.status}>"
        )


class Answer(Base, IDMixin, TimestampMixin):
    """Bir urinish ichidagi savol javobi.

    Savol turiga qarab quyidagi maydonlardan biri to'ldiriladi:
        - selected_option_ids: single/multiple/true_false
        - text_answer: short_text, essay
        - code_answer: code
        - file_url + file_size_bytes: file_upload
    """

    __tablename__ = "exam_answers"

    attempt_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("exam_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("exam_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Javob (savol turiga qarab)
    selected_option_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    text_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    code_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Scoring (NULL = hali baholanmagan)
    auto_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    points_earned: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0"), nullable=False
    )
    points_max: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    graded_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    graded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    grader_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Phase 9e — plagiat AI
    plagiarism_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    plagiarism_match_answer_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("exam_answers.id", ondelete="SET NULL"),
        nullable=True,
    )
    plagiarism_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    attempt: Mapped["ExamAttempt"] = relationship("ExamAttempt", back_populates="answers")
    question: Mapped["Question"] = relationship("Question")

    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_answer_attempt_question"),
    )

    def __repr__(self) -> str:
        return f"<Answer id={self.id} attempt={self.attempt_id} q={self.question_id}>"


class ProctoringEvent(Base, IDMixin):
    """Imtihon davomida qayd qilingan hodisalar (anti-cheat / face / audio).

    `event_type` qiymatlari:
        'tab_switch', 'visibility_lost', 'visibility_returned',
        'fullscreen_exit', 'fullscreen_entered',
        'copy_attempt', 'paste_attempt', 'context_menu',
        'face_lost', 'face_found', 'multiple_faces',
        'loud_audio', 'voice_detected',
        'devtools_opened', 'browser_resized',
        'network_loss', 'network_restored',
        'manual_flag'

    `severity`: 'info' | 'warning' | 'critical'
    """

    __tablename__ = "exam_proctoring_events"

    attempt_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("exam_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(
        String(10), default="info", nullable=False
    )
    event_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    __table_args__ = (
        # Phase 8c — review tab attempt timeline'ini chiqarish uchun.
        Index("ix_proctoring_events_attempt_at", "attempt_id", "occurred_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ProctoringEvent id={self.id} attempt={self.attempt_id} "
            f"type={self.event_type} sev={self.severity}>"
        )


class ProctoringSnapshot(Base, IDMixin):
    """Kamera frame snapshot — har 30 sekundda yuklanadi.

    Phase 6f'da face-api.js'dan kelgan `face_count` ham yoziladi.
    Phase 9a'da `face_match_score` (0..1) qo'shildi — reference rasm bilan
    cosine similarity (lokal hisoblanadi, server faqat saqlaydi).
    """

    __tablename__ = "exam_proctoring_snapshots"

    attempt_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("exam_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    face_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    face_match_score: Mapped[float | None] = mapped_column(
        Numeric(6, 4), nullable=True
    )
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bytes_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return (
            f"<ProctoringSnapshot id={self.id} attempt={self.attempt_id} "
            f"faces={self.face_count} match={self.face_match_score}>"
        )


class CodeTestCase(Base, IDMixin, TimestampMixin):
    """Code-type savol uchun test case — Phase 9d.

    Talaba kodi `stdin` ga uzatiladi va `expected_stdout` bilan solishtiriladi.
    `is_hidden=True` bo'lsa, talabaga ko'rsatilmaydi (kelajak final submission'da).
    `weight` (0..1) — test case'lar orasidagi nisbiy og'irlik (default 1.0).
    """

    __tablename__ = "exam_code_test_cases"

    question_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("exam_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stdin: Mapped[str] = mapped_column(Text, nullable=False, default="")
    expected_stdout: Mapped[str] = mapped_column(Text, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    weight: Mapped[float] = mapped_column(
        Numeric(4, 2), default=1.0, nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<CodeTestCase id={self.id} q={self.question_id} "
            f"order={self.order_index} hidden={self.is_hidden}>"
        )


class IdReferencePhoto(Base, IDMixin):
    """Imtihon boshlanishida olingan talaba yuz reference rasmi.

    Phase 6f'da: har snapshot shu rasm bilan compare qilinadi (face match).
    """

    __tablename__ = "exam_id_reference_photos"

    attempt_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("exam_attempts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def __repr__(self) -> str:
        return f"<IdReferencePhoto id={self.id} attempt={self.attempt_id}>"

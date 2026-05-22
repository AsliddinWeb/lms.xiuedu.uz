"""Exams Pydantic schemalari — Phase 6a."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ExamType = Literal["midterm", "final", "quiz", "dak"]
ExamStatus = Literal["draft", "published", "archived"]
QuestionType = Literal[
    "single_choice",
    "multiple_choice",
    "true_false",
    "short_text",
    "essay",
    "code",
    "file_upload",
]


# ============================================================================
# Question Option
# ============================================================================


class QuestionOptionCreate(BaseModel):
    text: str = Field(min_length=1)
    is_correct: bool = False
    explanation: str | None = None
    order_index: int = 0


class QuestionOptionPublic(BaseModel):
    """Pedagog ko'rinishi (is_correct ham bor)."""

    id: int
    text: str
    is_correct: bool
    explanation: str | None = None
    order_index: int

    model_config = ConfigDict(from_attributes=True)


class QuestionOptionStudent(BaseModel):
    """Talaba ko'rinishi (is_correct yashirin)."""

    id: int
    text: str
    order_index: int

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Question
# ============================================================================


class QuestionCreate(BaseModel):
    type: QuestionType
    title: str = Field(min_length=1)
    explanation: str | None = None
    points: Decimal = Field(default=Decimal("1.0"), ge=Decimal("0"), le=Decimal("999"))
    required: bool = True
    order_index: int = 0

    # Type-specific
    code_language: str | None = None
    code_initial: str | None = None
    max_file_size_mb: int | None = Field(default=None, ge=1, le=200)
    allowed_file_types: list[str] | None = None

    # short_text
    exact_match: bool = True
    case_sensitive: bool = False
    correct_text: str | None = None
    alternative_answers: list[str] | None = None

    # Options (single/multiple/true_false uchun)
    options: list[QuestionOptionCreate] = Field(default_factory=list)


class QuestionUpdate(BaseModel):
    type: QuestionType | None = None
    title: str | None = Field(default=None, min_length=1)
    explanation: str | None = None
    points: Decimal | None = Field(default=None, ge=Decimal("0"), le=Decimal("999"))
    required: bool | None = None
    order_index: int | None = None

    code_language: str | None = None
    code_initial: str | None = None
    max_file_size_mb: int | None = Field(default=None, ge=1, le=200)
    allowed_file_types: list[str] | None = None

    exact_match: bool | None = None
    case_sensitive: bool | None = None
    correct_text: str | None = None
    alternative_answers: list[str] | None = None

    options: list[QuestionOptionCreate] | None = None


class QuestionPublic(BaseModel):
    """Pedagog (yoki o'qib bo'lgan talaba) ko'rinishi — to'g'ri javoblar ham bor."""

    id: int
    exam_id: int
    type: QuestionType
    title: str
    explanation: str | None
    points: Decimal
    required: bool
    order_index: int

    code_language: str | None
    code_initial: str | None
    max_file_size_mb: int | None
    allowed_file_types: list[str] | None

    exact_match: bool
    case_sensitive: bool
    correct_text: str | None
    alternative_answers: list[str] | None

    options: list[QuestionOptionPublic] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuestionStudent(BaseModel):
    """Talaba ko'rinishi (correct javoblar yashirin, alternative_answers/explanation yashirin)."""

    id: int
    exam_id: int
    type: QuestionType
    title: str
    points: Decimal
    required: bool
    order_index: int

    code_language: str | None
    code_initial: str | None
    max_file_size_mb: int | None
    allowed_file_types: list[str] | None

    options: list[QuestionOptionStudent] = []

    model_config = ConfigDict(from_attributes=True)


class QuestionReorderRequest(BaseModel):
    ids: list[int] = Field(min_length=1)


# ============================================================================
# Exam
# ============================================================================


class ExamCreateRequest(BaseModel):
    course_id: int
    lesson_id: int | None = None

    title: str = Field(min_length=2, max_length=500)
    description: str | None = None
    type: ExamType = "quiz"

    duration_minutes: int = Field(ge=1, le=600)
    max_attempts: int = Field(default=1, ge=1, le=20)
    passing_score: Decimal = Field(
        default=Decimal("60"), ge=Decimal("0"), le=Decimal("100")
    )
    shuffle_questions: bool = True
    shuffle_options: bool = True
    show_correct_answers: bool = False
    question_count: int | None = Field(default=None, ge=1)

    proctoring_enabled: bool = True
    require_face_id: bool = True
    require_screen_share: bool = True
    allow_tab_switch: bool = False
    max_face_loss_seconds: int = Field(default=10, ge=3, le=120)

    available_from: datetime | None = None
    available_until: datetime | None = None


class ExamUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=500)
    description: str | None = None
    type: ExamType | None = None
    lesson_id: int | None = None

    duration_minutes: int | None = Field(default=None, ge=1, le=600)
    max_attempts: int | None = Field(default=None, ge=1, le=20)
    passing_score: Decimal | None = Field(
        default=None, ge=Decimal("0"), le=Decimal("100")
    )
    shuffle_questions: bool | None = None
    shuffle_options: bool | None = None
    show_correct_answers: bool | None = None
    question_count: int | None = Field(default=None, ge=1)

    proctoring_enabled: bool | None = None
    require_face_id: bool | None = None
    require_screen_share: bool | None = None
    allow_tab_switch: bool | None = None
    max_face_loss_seconds: int | None = Field(default=None, ge=3, le=120)

    available_from: datetime | None = None
    available_until: datetime | None = None


class ExamPublic(BaseModel):
    id: int
    course_id: int
    lesson_id: int | None
    organization_id: int | None

    title: str
    description: str | None
    type: ExamType
    status: ExamStatus

    duration_minutes: int
    max_attempts: int
    passing_score: Decimal
    shuffle_questions: bool
    shuffle_options: bool
    show_correct_answers: bool
    question_count: int | None

    proctoring_enabled: bool
    require_face_id: bool
    require_screen_share: bool
    allow_tab_switch: bool
    max_face_loss_seconds: int

    available_from: datetime | None
    available_until: datetime | None
    closed_at: datetime | None

    created_by: int
    created_at: datetime
    updated_at: datetime

    # Statistika (computed): savollar soni, jami ball
    total_questions: int = 0
    total_points: Decimal = Decimal("0")

    model_config = ConfigDict(from_attributes=True)


class PaginatedExams(BaseModel):
    items: list[ExamPublic]
    total: int


# ============================================================================
# Attempt + Answer
# ============================================================================


AttemptStatus = Literal[
    "in_progress",
    "submitted",
    "auto_submitted",
    "graded",
    "flagged",
    "invalidated",
]


class AnswerSubmit(BaseModel):
    """Talaba bitta savolga javob saqlaydi (savol turiga mos field to'ldiriladi)."""

    question_id: int
    selected_option_ids: list[int] | None = None
    text_answer: str | None = None
    code_answer: str | None = None
    file_url: str | None = None
    file_size_bytes: int | None = None


class AnswerPublic(BaseModel):
    """Pedagog ko'rinishi (auto_correct + points + grader_comment ham bor)."""

    id: int
    attempt_id: int
    question_id: int
    selected_option_ids: list[int] | None = None
    text_answer: str | None = None
    code_answer: str | None = None
    file_url: str | None = None
    file_size_bytes: int | None = None
    auto_correct: bool | None = None
    points_earned: Decimal
    points_max: Decimal | None = None
    graded_by: int | None = None
    graded_at: datetime | None = None
    grader_comment: str | None = None
    # Phase 9e — plagiat
    plagiarism_score: Decimal | None = None
    plagiarism_match_answer_id: int | None = None
    plagiarism_checked_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttemptPublic(BaseModel):
    """Pedagog/admin ko'rinishi — barcha maydonlar."""

    id: int
    exam_id: int
    user_id: int
    attempt_number: int
    status: AttemptStatus
    started_at: datetime
    submitted_at: datetime | None
    deadline_at: datetime
    time_spent_seconds: int

    auto_score: Decimal | None
    manual_score: Decimal | None
    total_score: Decimal | None
    max_score: Decimal | None
    percentage: Decimal | None
    passed: bool | None

    violation_score: int
    flagged: bool
    # Phase 9f — smart anomaly scoring
    smart_score: int = 0
    smart_flags: list[dict] | None = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttemptStudentSummary(BaseModel):
    """Talaba o'z urinishi haqida qisqacha ma'lumot."""

    id: int
    exam_id: int
    attempt_number: int
    status: AttemptStatus
    started_at: datetime
    submitted_at: datetime | None
    deadline_at: datetime
    time_spent_seconds: int
    total_score: Decimal | None
    max_score: Decimal | None
    percentage: Decimal | None
    passed: bool | None

    model_config = ConfigDict(from_attributes=True)


class AttemptTakeView(BaseModel):
    """Imtihon yechish ekranida talabaga ko'rinadigan ma'lumot.

    Savollar `QuestionStudent` formatida (to'g'ri javoblar yashirin).
    Question.order = bu attempt uchun shuffled tartib.
    Saqlangan javoblar `answers` ichida (yana yozish/yangilash uchun).
    """

    id: int
    exam_id: int
    attempt_number: int
    status: AttemptStatus
    started_at: datetime
    deadline_at: datetime
    duration_minutes: int

    questions: list[QuestionStudent]
    saved_answers: list[AnswerSubmit] = []

    model_config = ConfigDict(from_attributes=True)


class AttemptResult(BaseModel):
    """Submit qilingandan keyingi natija ko'rinishi (talaba uchun)."""

    id: int
    exam_id: int
    attempt_number: int
    status: AttemptStatus
    submitted_at: datetime | None
    time_spent_seconds: int
    auto_score: Decimal | None
    manual_score: Decimal | None
    total_score: Decimal | None
    max_score: Decimal | None
    percentage: Decimal | None
    passed: bool | None

    # show_correct_answers=True bo'lsa, javoblar ham qaytariladi
    answers: list[AnswerPublic] = []

    model_config = ConfigDict(from_attributes=True)


class GradeAnswerRequest(BaseModel):
    """Pedagog bitta javobni qo'lda baholaydi (essay/code/file_upload)."""

    answer_id: int
    points_earned: Decimal = Field(ge=Decimal("0"))
    grader_comment: str | None = None


class GradeAttemptRequest(BaseModel):
    """Pedagog bir nechta javobni bir vaqtning o'zida baholaydi."""

    grades: list[GradeAnswerRequest] = Field(min_length=1)


class InvalidateAttemptRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class PaginatedAttempts(BaseModel):
    items: list[AttemptPublic]
    total: int


# ============================================================================
# Proctoring (Phase 6f)
# ============================================================================


ProctoringSeverity = Literal["info", "warning", "critical"]


class ProctoringEventCreate(BaseModel):
    event_type: str = Field(min_length=1, max_length=40)
    severity: ProctoringSeverity = "info"
    metadata: dict | None = None
    occurred_at: datetime | None = None


class ProctoringEventPublic(BaseModel):
    id: int
    attempt_id: int
    event_type: str
    severity: ProctoringSeverity
    event_metadata: dict | None = None
    occurred_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProctoringSnapshotPublic(BaseModel):
    id: int
    attempt_id: int
    object_key: str
    url: str
    face_count: int | None
    face_match_score: Decimal | None = None
    width: int | None
    height: int | None
    bytes_size: int | None
    captured_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IdReferencePhotoPublic(BaseModel):
    id: int
    attempt_id: int
    url: str
    captured_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ViolationScorePublic(BaseModel):
    attempt_id: int
    violation_score: int
    flagged: bool


# Phase 7c — HEMIS sync log
class HemisSyncLogPublic(BaseModel):
    id: int
    sync_type: str
    target_id: int | None
    status: str
    attempts: int
    payload: dict | None = None
    response: dict | None = None
    last_error: str | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedHemisSyncLogs(BaseModel):
    items: list[HemisSyncLogPublic]
    total: int


# Phase 9d — Code test cases + run
class CodeTestCaseCreate(BaseModel):
    stdin: str = ""
    expected_stdout: str = Field(min_length=1, max_length=10000)
    is_hidden: bool = False
    weight: float = Field(default=1.0, ge=0, le=100)
    order_index: int | None = None


class CodeTestCaseUpdate(BaseModel):
    stdin: str | None = None
    expected_stdout: str | None = Field(default=None, min_length=1, max_length=10000)
    is_hidden: bool | None = None
    weight: float | None = Field(default=None, ge=0, le=100)
    order_index: int | None = None


class CodeTestCasePublic(BaseModel):
    id: int
    question_id: int
    order_index: int
    stdin: str
    expected_stdout: str
    is_hidden: bool
    weight: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CodeTestCaseStudent(BaseModel):
    """Talabaga ko'rinadi (faqat visible) — expected_stdout yashirin emas."""
    id: int
    order_index: int
    stdin: str
    expected_stdout: str

    model_config = ConfigDict(from_attributes=True)


class CodeRunRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50000)


class CodeRunResultItem(BaseModel):
    test_case_id: int
    is_hidden: bool
    passed: bool
    stdout: str
    stderr: str
    exit_code: int
    runtime_ms: int
    timed_out: bool
    expected_stdout: str | None = None  # talaba ko'radi (faqat visible)


class CodeRunResponse(BaseModel):
    results: list[CodeRunResultItem]
    passed_count: int
    total: int

"""Assignments Pydantic schemalari (Phase 4a)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

AssignmentType = Literal["essay", "file"]
SubmissionStatus = Literal["submitted", "grading", "graded", "returned"]


# ============================================================================
# Assignment
# ============================================================================


class AssignmentCreateRequest(BaseModel):
    course_id: int
    lesson_id: int | None = None

    title: str = Field(min_length=2, max_length=500)
    description: str | None = None
    instructions: str | None = None

    type: AssignmentType

    available_from: datetime | None = None
    due_date: datetime
    closed_at: datetime | None = None

    max_score: Decimal = Field(default=Decimal("100"), ge=Decimal("0"), le=Decimal("999.99"))
    pass_score: Decimal | None = Field(default=None, ge=Decimal("0"))
    weight_percent: Decimal | None = Field(
        default=None, ge=Decimal("0"), le=Decimal("100")
    )

    max_attempts: int = Field(default=1, ge=1, le=20)
    late_submission_allowed: bool = True
    late_penalty_per_day: Decimal = Field(
        default=Decimal("0"), ge=Decimal("0"), le=Decimal("100")
    )

    allowed_file_types: list[str] = Field(default_factory=list)
    max_file_size_mb: int = Field(default=50, ge=1, le=200)

    is_published: bool = False
    rubric_id: int | None = None

    plagiarism_check_enabled: bool = False
    plagiarism_threshold: Decimal = Field(
        default=Decimal("30"), ge=Decimal("0"), le=Decimal("100")
    )
    peer_review_enabled: bool = False
    peer_reviews_per_submission: int = Field(default=3, ge=1, le=10)

    @model_validator(mode="after")
    def _check_dates_and_pass(self) -> "AssignmentCreateRequest":
        if self.available_from and self.available_from >= self.due_date:
            raise ValueError("available_from due_date'dan oldin bo'lishi kerak")
        if self.closed_at and self.closed_at < self.due_date:
            raise ValueError(
                "closed_at due_date'dan keyin yoki teng bo'lishi kerak"
            )
        if self.pass_score is not None and self.pass_score > self.max_score:
            raise ValueError("pass_score max_score dan oshmasligi kerak")
        # Tag uzunligi cheklovi
        for ft in self.allowed_file_types:
            if not ft.strip() or len(ft) > 20:
                raise ValueError(f"allowed_file_types element noto'g'ri: {ft!r}")
        return self


class AssignmentUpdateRequest(BaseModel):
    lesson_id: int | None = None

    title: str | None = Field(default=None, min_length=2, max_length=500)
    description: str | None = None
    instructions: str | None = None

    available_from: datetime | None = None
    due_date: datetime | None = None
    closed_at: datetime | None = None

    max_score: Decimal | None = Field(default=None, ge=Decimal("0"), le=Decimal("999.99"))
    pass_score: Decimal | None = Field(default=None, ge=Decimal("0"))
    weight_percent: Decimal | None = Field(
        default=None, ge=Decimal("0"), le=Decimal("100")
    )

    max_attempts: int | None = Field(default=None, ge=1, le=20)
    late_submission_allowed: bool | None = None
    late_penalty_per_day: Decimal | None = Field(
        default=None, ge=Decimal("0"), le=Decimal("100")
    )

    allowed_file_types: list[str] | None = None
    max_file_size_mb: int | None = Field(default=None, ge=1, le=200)
    rubric_id: int | None = None

    plagiarism_check_enabled: bool | None = None
    plagiarism_threshold: Decimal | None = Field(
        default=None, ge=Decimal("0"), le=Decimal("100")
    )
    peer_review_enabled: bool | None = None
    peer_reviews_per_submission: int | None = Field(default=None, ge=1, le=10)


class AssignmentPublishRequest(BaseModel):
    is_published: bool


class AssignmentPublic(BaseModel):
    id: int
    course_id: int
    lesson_id: int | None

    title: str
    description: str | None
    instructions: str | None

    type: str

    available_from: datetime | None
    due_date: datetime
    closed_at: datetime | None

    max_score: Decimal
    pass_score: Decimal | None
    weight_percent: Decimal | None

    max_attempts: int
    late_submission_allowed: bool
    late_penalty_per_day: Decimal

    allowed_file_types: list[str]
    max_file_size_mb: int

    is_published: bool
    rubric_id: int | None

    plagiarism_check_enabled: bool
    plagiarism_threshold: Decimal
    peer_review_enabled: bool
    peer_reviews_per_submission: int

    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedAssignments(BaseModel):
    items: list[AssignmentPublic]
    total: int


# ============================================================================
# Submission
# ============================================================================


class SubmissionFile(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1, max_length=2048)
    mime: str = Field(default="application/octet-stream", max_length=100)
    size: int = Field(default=0, ge=0)


class SubmissionCreateRequest(BaseModel):
    """Talaba topshirig'ini yaratish.

    Fayllarni avval `/assignments/{id}/upload` orqali yuklab, qaytgan
    `{name, url, mime, size}` obyektlarini `files` arrayga qo'yib jo'natamiz.
    """

    content: str | None = None
    files: list[SubmissionFile] = Field(default_factory=list)

    @model_validator(mode="after")
    def _has_content_or_files(self) -> "SubmissionCreateRequest":
        has_content = bool((self.content or "").strip())
        has_files = len(self.files) > 0
        if not has_content and not has_files:
            raise ValueError("content yoki files (kamida bittasi) majburiy")
        return self


class SubmissionUploadResponse(BaseModel):
    """`/assignments/{id}/upload` javobi — fayl URL + meta."""

    name: str
    url: str
    mime: str
    size: int


class SubmissionPublic(BaseModel):
    id: int
    assignment_id: int
    user_id: int
    user_full_name: str | None = None
    user_email: str | None = None
    attempt_number: int

    content: str | None
    files: list[dict[str, Any]]

    submitted_at: datetime
    is_late: bool
    days_late: int

    status: str

    score: Decimal | None
    final_score: Decimal | None
    grade_letter: str | None
    feedback: str | None
    rubric_scores: dict[str, Any]
    annotations: list[dict[str, Any]]

    plagiarism_score: Decimal | None
    plagiarism_report_url: str | None
    plagiarism_flagged: bool
    plagiarism_checked_at: datetime | None

    graded_by: int | None
    graded_by_full_name: str | None = None
    graded_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class PaginatedSubmissions(BaseModel):
    items: list[SubmissionPublic]
    total: int


# ============================================================================
# Rubric (Phase 4b)
# ============================================================================


class RubricLevel(BaseModel):
    label: str = Field(min_length=1, max_length=50)
    points: Decimal = Field(ge=Decimal("0"))
    description: str | None = Field(default=None, max_length=500)


class RubricCriterion(BaseModel):
    key: str = Field(min_length=1, max_length=50, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1, max_length=120)
    max_points: Decimal = Field(ge=Decimal("0"))
    levels: list[RubricLevel] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_levels(self) -> "RubricCriterion":
        for level in self.levels:
            if level.points > self.max_points:
                raise ValueError(
                    f"'{self.key}' kriteriyasi: '{level.label}' levelidagi "
                    f"points={level.points} max_points={self.max_points} dan oshmasin"
                )
        return self


class RubricCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    organization_id: int | None = None
    criteria: list[RubricCriterion] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_unique_keys(self) -> "RubricCreateRequest":
        keys = [c.key for c in self.criteria]
        if len(set(keys)) != len(keys):
            raise ValueError("Kriteriya kalitlari ('key') yagona bo'lishi shart")
        return self


class RubricUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    organization_id: int | None = None
    criteria: list[RubricCriterion] | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _check_unique_keys(self) -> "RubricUpdateRequest":
        if self.criteria is not None:
            keys = [c.key for c in self.criteria]
            if len(set(keys)) != len(keys):
                raise ValueError("Kriteriya kalitlari ('key') yagona bo'lishi shart")
        return self


class RubricPublic(BaseModel):
    id: int
    title: str
    description: str | None
    total_points: Decimal
    criteria: list[dict[str, Any]]
    organization_id: int | None
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedRubrics(BaseModel):
    items: list[RubricPublic]
    total: int


# ============================================================================
# Grade flow (Phase 4b)
# ============================================================================


GradeLetter = Literal["A", "B", "C", "D", "F"]


class GradeRequest(BaseModel):
    """Pedagog tomonidan submission baholash.

    Agar `rubric_scores` ko'rsatilsa, `score` jami orqali avtomatik hisoblanadi
    (kalitlar Assignment.rubric.criteria bilan mos kelishi shart).
    Aks holda `score` to'g'ridan-to'g'ri ishlatiladi.
    """

    score: Decimal | None = Field(default=None, ge=Decimal("0"))
    rubric_scores: dict[str, Decimal] | None = None
    grade_letter: GradeLetter | None = None
    feedback: str | None = None
    return_for_revision: bool = False

    @model_validator(mode="after")
    def _check_one_provided(self) -> "GradeRequest":
        if self.score is None and not self.rubric_scores:
            raise ValueError(
                "score yoki rubric_scores (kamida bittasi) majburiy"
            )
        return self


class AnnotationItem(BaseModel):
    """Bitta inline annotation. Frontend foydalanish uchun erkin sxema —
    PDF/text uchun: page, x, y, w, h, text, color va h.k.
    """

    page: int | None = None
    x: float | None = None
    y: float | None = None
    w: float | None = None
    h: float | None = None
    text: str = Field(min_length=1, max_length=2000)
    color: str | None = Field(default=None, max_length=20)


class AnnotationsUpdateRequest(BaseModel):
    """Submission annotationlarini to'liq almashtirish."""

    annotations: list[AnnotationItem] = Field(default_factory=list)


# ============================================================================
# Plagiat (Phase 4e)
# ============================================================================


class PlagiarismCheckResult(BaseModel):
    submission_id: int
    plagiarism_score: Decimal | None
    plagiarism_report_url: str | None
    plagiarism_flagged: bool
    plagiarism_checked_at: datetime | None


# ============================================================================
# Peer review (Phase 4e)
# ============================================================================


class PeerReviewSubmitRequest(BaseModel):
    score: Decimal | None = Field(default=None, ge=Decimal("0"))
    rubric_scores: dict[str, Decimal] | None = None
    feedback: str | None = None

    @model_validator(mode="after")
    def _check_one_provided(self) -> "PeerReviewSubmitRequest":
        if self.score is None and not self.rubric_scores:
            raise ValueError("score yoki rubric_scores (kamida bittasi) majburiy")
        return self


class PeerReviewPublic(BaseModel):
    """Peer review — talabaga (anonim, submission egasi yashirin)."""

    id: int
    submission_id: int
    # Reviewer'ning o'zi sifatida ko'radi — boshqa talabaga ko'rinmaydi
    reviewer_id: int
    score: Decimal | None
    feedback: str | None
    rubric_scores: dict[str, Any]
    submitted_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PeerReviewStartResponse(BaseModel):
    assignment_id: int
    created: int
    total: int


# ============================================================================
# Appeals (Phase 4e)
# ============================================================================


AppealStatus = Literal["pending", "approved", "rejected"]


class AppealCreateRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=2000)


class AppealRespondRequest(BaseModel):
    status: Literal["approved", "rejected"]
    new_score: Decimal | None = Field(default=None, ge=Decimal("0"))
    response: str | None = Field(default=None, max_length=2000)


class AppealPublic(BaseModel):
    id: int
    submission_id: int
    student_id: int
    student_full_name: str | None = None
    student_email: str | None = None
    reason: str
    status: str
    new_score: Decimal | None
    response: str | None
    reviewed_by: int | None
    reviewed_by_full_name: str | None = None
    reviewed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedAppeals(BaseModel):
    items: list[AppealPublic]
    total: int

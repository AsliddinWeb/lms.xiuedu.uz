"""Courses Pydantic schemalari (Phase 3b)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CourseType = Literal["academic", "open", "micro", "specialization"]
CourseLevel = Literal["beginner", "intermediate", "advanced"]
CourseStatus = Literal["draft", "published", "archived"]
EnrollmentType = Literal["auto", "manual", "self"]
EnrollmentMethod = Literal["auto", "manual", "self"]
CompletionStatus = Literal["in_progress", "completed", "failed", "dropped"]
LanguageCode = Literal["uz-lat", "uz-cyr", "ru", "en"]


# ============================================================================
# Course
# ============================================================================


class CourseCreateRequest(BaseModel):
    code: str | None = Field(default=None, max_length=50)
    title: str = Field(min_length=2, max_length=500)
    slug: str = Field(min_length=2, max_length=200, pattern=r"^[a-z0-9][a-z0-9-]*$")
    description: str | None = None

    subject_id: int | None = None
    organization_id: int | None = None

    type: CourseType = "academic"
    level: CourseLevel | None = None
    language: LanguageCode = "uz-lat"

    cover_image_url: str | None = Field(default=None, max_length=2048)
    trailer_video_url: str | None = Field(default=None, max_length=2048)

    duration_weeks: int | None = Field(default=None, ge=1, le=104)
    estimated_hours: int | None = Field(default=None, ge=1, le=10000)

    objectives: list[str] = Field(default_factory=list)
    skills_gained: list[str] = Field(default_factory=list)

    enrollment_type: EnrollmentType = "manual"
    max_students: int | None = Field(default=None, ge=1)


class CourseUpdateRequest(BaseModel):
    code: str | None = Field(default=None, max_length=50)
    title: str | None = Field(default=None, min_length=2, max_length=500)
    description: str | None = None

    subject_id: int | None = None
    organization_id: int | None = None

    type: CourseType | None = None
    level: CourseLevel | None = None
    language: LanguageCode | None = None

    cover_image_url: str | None = Field(default=None, max_length=2048)
    trailer_video_url: str | None = Field(default=None, max_length=2048)

    duration_weeks: int | None = Field(default=None, ge=1, le=104)
    estimated_hours: int | None = Field(default=None, ge=1, le=10000)

    objectives: list[str] | None = None
    skills_gained: list[str] | None = None

    enrollment_type: EnrollmentType | None = None
    max_students: int | None = Field(default=None, ge=1)


class CoursePublic(BaseModel):
    id: int
    code: str | None
    title: str
    slug: str
    description: str | None
    subject_id: int | None
    organization_id: int | None

    type: str
    level: str | None
    language: str

    cover_image_url: str | None
    trailer_video_url: str | None

    duration_weeks: int | None
    estimated_hours: int | None

    objectives: list[str]
    skills_gained: list[str]

    status: str
    published_at: datetime | None

    enrollment_type: str
    max_students: int | None

    primary_author_id: int | None

    # Ro'yxat javobida to'ldiriladi (yozilgan talabalar soni) — ixtiyoriy
    enrollment_count: int | None = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedCourses(BaseModel):
    items: list[CoursePublic]
    total: int


# ============================================================================
# Module
# ============================================================================


class ModuleCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=500)
    description: str | None = None
    order_index: int | None = Field(default=None, ge=0)
    available_from: datetime | None = None
    available_until: datetime | None = None


class ModuleUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=500)
    description: str | None = None
    order_index: int | None = Field(default=None, ge=0)
    available_from: datetime | None = None
    available_until: datetime | None = None


class ModulePublic(BaseModel):
    id: int
    course_id: int
    title: str
    description: str | None
    order_index: int
    available_from: datetime | None
    available_until: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReorderRequest(BaseModel):
    """Module/Lesson reorder uchun ID'lar tartibi."""

    ordered_ids: list[int] = Field(min_length=1)

    @field_validator("ordered_ids")
    @classmethod
    def _unique(cls, v: list[int]) -> list[int]:
        if len(set(v)) != len(v):
            raise ValueError("ordered_ids ichida duplicate id bor")
        return v


# ============================================================================
# Lesson
# ============================================================================


class LessonCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=500)
    description: str | None = None
    order_index: int | None = Field(default=None, ge=0)
    primary_content_id: int | None = None
    estimated_minutes: int | None = Field(default=None, ge=0, le=600)
    is_required_for_completion: bool = True


class LessonUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=500)
    description: str | None = None
    order_index: int | None = Field(default=None, ge=0)
    primary_content_id: int | None = None
    estimated_minutes: int | None = Field(default=None, ge=0, le=600)
    is_required_for_completion: bool | None = None


class LessonPublic(BaseModel):
    id: int
    module_id: int
    title: str
    description: str | None
    order_index: int
    primary_content_id: int | None
    estimated_minutes: int | None
    is_required_for_completion: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Enrollment
# ============================================================================


class EnrollmentCreateRequest(BaseModel):
    """Admin/teacher tomonidan talaba qo'shish."""

    user_id: int
    enrollment_method: EnrollmentMethod = "manual"


class EnrollmentPublic(BaseModel):
    id: int
    course_id: int
    user_id: int
    enrolled_at: datetime
    enrollment_method: str
    enrolled_by: int | None
    completion_status: str
    completed_at: datetime | None
    final_grade: Decimal | None

    model_config = ConfigDict(from_attributes=True)


class EnrollmentStudentItem(BaseModel):
    """`/courses/{id}/students` javob elementi."""

    enrollment_id: int
    user_id: int
    full_name: str
    email: str
    enrolled_at: datetime
    enrollment_method: str
    completion_status: str
    progress_percent: Decimal


class PaginatedStudents(BaseModel):
    items: list[EnrollmentStudentItem]
    total: int


class TeacherStudentItem(BaseModel):
    """`/me/students` — pedagog barcha kurslari bo'yicha noyob talaba (aggregate)."""

    user_id: int
    full_name: str
    email: str | None
    avatar_url: str | None
    group_name: str | None
    course_count: int       # shu pedagog kurslaridan nechtasida
    completed_count: int    # tugatgan kurslar soni
    avg_grade: float | None  # o'rtacha yakuniy baho


class PaginatedTeacherStudents(BaseModel):
    items: list[TeacherStudentItem]
    total: int


# ============================================================================
# LessonProgress
# ============================================================================


class LessonProgressUpsertRequest(BaseModel):
    progress_percent: Decimal = Field(ge=Decimal("0"), le=Decimal("100"))
    time_spent_seconds: int | None = Field(default=None, ge=0)
    last_position: dict[str, Any] | None = None


class LessonProgressPublic(BaseModel):
    id: int
    user_id: int
    lesson_id: int
    started_at: datetime | None
    completed_at: datetime | None
    progress_percent: Decimal
    time_spent_seconds: int
    last_position: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class CourseProgressPublic(BaseModel):
    """`/courses/{id}/my-progress` javobi — kurs bo'yicha umumiy."""

    course_id: int
    enrolled: bool
    completion_status: str | None
    completed_lessons: int
    total_required_lessons: int
    percent: Decimal
    completed_at: datetime | None

"""Academic Pydantic schemas — Organization/Faculty/Department/Specialty/Subject/Curriculum/AcademicCalendar."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


# ============================================================================
# Organization
# ============================================================================


class OrgCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=20)
    name: str = Field(min_length=2, max_length=300)
    short_name: str | None = Field(default=None, max_length=100)
    type: Literal["state", "private", "foreign"] | None = None
    license_number: str | None = Field(default=None, max_length=100)
    rector_id: int | None = None
    address: str | None = None
    phone: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    website: str | None = Field(default=None, max_length=255)
    domain: str | None = Field(default=None, max_length=100)
    logo_url: str | None = None
    branding: dict[str, Any] = Field(default_factory=dict)
    settings: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class OrgUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=300)
    short_name: str | None = Field(default=None, max_length=100)
    type: Literal["state", "private", "foreign"] | None = None
    license_number: str | None = Field(default=None, max_length=100)
    rector_id: int | None = None
    address: str | None = None
    phone: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    website: str | None = Field(default=None, max_length=255)
    domain: str | None = Field(default=None, max_length=100)
    logo_url: str | None = None
    branding: dict[str, Any] | None = None
    settings: dict[str, Any] | None = None
    is_active: bool | None = None


class OrgPublic(BaseModel):
    id: int
    code: str
    name: str
    short_name: str | None
    type: str | None
    license_number: str | None
    rector_id: int | None
    address: str | None
    phone: str | None
    email: str | None
    website: str | None
    domain: str | None
    logo_url: str | None
    branding: dict[str, Any]
    settings: dict[str, Any]
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Faculty
# ============================================================================


class FacultyCreateRequest(BaseModel):
    # Single-tenant XIU: ixtiyoriy. Service avtomatik XIU id'siga to'ldiradi
    organization_id: int | None = None
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=2, max_length=200)
    short_name: str | None = Field(default=None, max_length=50)
    dean_id: int | None = None
    is_active: bool = True


class FacultyUpdateRequest(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=20)
    name: str | None = Field(default=None, min_length=2, max_length=200)
    short_name: str | None = Field(default=None, max_length=50)
    dean_id: int | None = None
    is_active: bool | None = None


class FacultyPublic(BaseModel):
    id: int
    organization_id: int
    code: str
    name: str
    short_name: str | None
    dean_id: int | None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Department
# ============================================================================


class DepartmentCreateRequest(BaseModel):
    faculty_id: int
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=2, max_length=200)
    head_id: int | None = None
    is_active: bool = True


class DepartmentUpdateRequest(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=20)
    name: str | None = Field(default=None, min_length=2, max_length=200)
    head_id: int | None = None
    is_active: bool | None = None


class DepartmentPublic(BaseModel):
    id: int
    faculty_id: int
    code: str
    name: str
    head_id: int | None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Specialty (559-qaror 14 + 15-band)
# ============================================================================

EducationLevel = Literal["bachelor", "master", "phd"]
EducationForm = Literal["fulltime", "parttime", "evening", "distance"]
LanguageCode = Literal["uz-lat", "uz-cyr", "ru", "en"]


class SpecialtyCreateRequest(BaseModel):
    department_id: int
    code: str = Field(min_length=2, max_length=50)  # DTS kodi
    name: str = Field(min_length=2, max_length=300)
    level: EducationLevel
    duration_years: int = Field(ge=1, le=8)
    education_form: EducationForm
    language: LanguageCode
    distance_enabled: bool = False
    annual_quota: int | None = Field(default=None, ge=0)
    is_active: bool = True

    @model_validator(mode="after")
    def _check_quota_per_level(self) -> "SpecialtyCreateRequest":
        """559-qaror 15-band: bakalavr 300, magistr 30."""
        if self.annual_quota is None:
            return self
        if self.level == "bachelor" and self.annual_quota > 300:
            raise ValueError("Bakalavr yo'nalishi uchun annual_quota maksimal 300")
        if self.level == "master" and self.annual_quota > 30:
            raise ValueError("Magistr yo'nalishi uchun annual_quota maksimal 30")
        return self


class SpecialtyUpdateRequest(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=50)
    name: str | None = Field(default=None, min_length=2, max_length=300)
    level: EducationLevel | None = None
    duration_years: int | None = Field(default=None, ge=1, le=8)
    education_form: EducationForm | None = None
    language: LanguageCode | None = None
    distance_enabled: bool | None = None
    annual_quota: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class SpecialtyPublic(BaseModel):
    id: int
    department_id: int
    code: str
    name: str
    level: str
    duration_years: int
    education_form: str
    language: str
    distance_enabled: bool
    annual_quota: int | None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Subject
# ============================================================================


class SubjectCreateRequest(BaseModel):
    department_id: int
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=2, max_length=200)
    short_name: str | None = Field(default=None, max_length=50)
    description: str | None = None
    credits: int = Field(ge=1, le=60)
    lecture_hours: int = Field(default=0, ge=0)
    practice_hours: int = Field(default=0, ge=0)
    seminar_hours: int = Field(default=0, ge=0)
    self_study_hours: int = Field(default=0, ge=0)
    language: LanguageCode = "uz-lat"
    prerequisite_ids: list[int] = Field(default_factory=list)
    is_active: bool = True


class SubjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    short_name: str | None = Field(default=None, max_length=50)
    description: str | None = None
    credits: int | None = Field(default=None, ge=1, le=60)
    lecture_hours: int | None = Field(default=None, ge=0)
    practice_hours: int | None = Field(default=None, ge=0)
    seminar_hours: int | None = Field(default=None, ge=0)
    self_study_hours: int | None = Field(default=None, ge=0)
    language: LanguageCode | None = None
    prerequisite_ids: list[int] | None = None
    is_active: bool | None = None


class SubjectPublic(BaseModel):
    id: int
    department_id: int
    code: str
    name: str
    short_name: str | None
    description: str | None
    credits: int
    lecture_hours: int
    practice_hours: int
    seminar_hours: int
    self_study_hours: int
    language: str
    prerequisite_ids: list[int] = Field(default_factory=list)
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Curriculum
# ============================================================================


class CurriculumSubjectIn(BaseModel):
    subject_id: int
    semester: int = Field(ge=1, le=20)
    is_required: bool = True


class CurriculumSubjectPublic(BaseModel):
    id: int
    curriculum_id: int
    subject_id: int
    semester: int
    is_required: bool

    model_config = ConfigDict(from_attributes=True)


class CurriculumCreateRequest(BaseModel):
    specialty_id: int
    name: str = Field(min_length=2, max_length=200)
    version: str | None = Field(default=None, max_length=20)
    valid_from: date
    valid_until: date | None = None
    based_on: str | None = Field(default=None, max_length=50)  # 'DTS' | ...
    standard_code: str | None = Field(default=None, max_length=50)
    total_credits: int = Field(ge=1, le=500)
    subjects: list[CurriculumSubjectIn] = Field(default_factory=list)

    @field_validator("valid_until")
    @classmethod
    def _check_valid_range(cls, v: date | None, info) -> date | None:
        if v is not None and "valid_from" in info.data and v < info.data["valid_from"]:
            raise ValueError("valid_until valid_from'dan keyin bo'lishi kerak")
        return v


class CurriculumUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    version: str | None = Field(default=None, max_length=20)
    valid_from: date | None = None
    valid_until: date | None = None
    based_on: str | None = Field(default=None, max_length=50)
    standard_code: str | None = Field(default=None, max_length=50)
    total_credits: int | None = Field(default=None, ge=1, le=500)
    is_active: bool | None = None


class CurriculumPublic(BaseModel):
    id: int
    specialty_id: int
    name: str
    version: str | None
    valid_from: date
    valid_until: date | None
    based_on: str | None
    standard_code: str | None
    total_credits: int
    is_active: bool
    approved_by: int | None
    approved_at: datetime | None
    created_at: datetime
    subjects: list[CurriculumSubjectPublic] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class CurriculumCloneRequest(BaseModel):
    new_version: str = Field(min_length=1, max_length=20)
    new_valid_from: date


# ============================================================================
# Academic calendar
# ============================================================================


class CalendarSemesterIn(BaseModel):
    name: str
    start_date: date
    end_date: date


class CalendarHolidayIn(BaseModel):
    name: str
    date: date
    days: int = 1


class AcademicCalendarCreateRequest(BaseModel):
    # Single-tenant XIU: ixtiyoriy. Service avtomatik XIU id'siga to'ldiradi
    organization_id: int | None = None
    academic_year: str = Field(pattern=r"^\d{4}-\d{4}$")  # '2026-2027'
    name: str = Field(min_length=2, max_length=100)
    start_date: date
    end_date: date
    semesters: list[CalendarSemesterIn] = Field(default_factory=list)
    holidays: list[CalendarHolidayIn] = Field(default_factory=list)
    is_active: bool = True

    @field_validator("end_date")
    @classmethod
    def _check_dates(cls, v: date, info) -> date:
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("end_date start_date'dan keyin bo'lishi kerak")
        return v


class AcademicCalendarUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    start_date: date | None = None
    end_date: date | None = None
    semesters: list[CalendarSemesterIn] | None = None
    holidays: list[CalendarHolidayIn] | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def _check_range(self) -> "AcademicCalendarUpdateRequest":
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date <= self.start_date
        ):
            raise ValueError("end_date start_date'dan keyin bo'lishi kerak")
        return self


class AcademicCalendarPublic(BaseModel):
    id: int
    organization_id: int
    academic_year: str
    name: str
    start_date: date
    end_date: date
    semesters: list[dict[str, Any]]
    holidays: list[dict[str, Any]]
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Pagination wrapper
# ============================================================================


class PaginatedFaculties(BaseModel):
    items: list[FacultyPublic]
    total: int


class PaginatedDepartments(BaseModel):
    items: list[DepartmentPublic]
    total: int


class PaginatedSpecialties(BaseModel):
    items: list[SpecialtyPublic]
    total: int


class PaginatedSubjects(BaseModel):
    items: list[SubjectPublic]
    total: int


class PaginatedCurricula(BaseModel):
    items: list[CurriculumPublic]
    total: int

"""Live darslar Pydantic schemalari (Phase 5a)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LiveProvider = Literal["native"]
LiveStatus = Literal["scheduled", "live", "ended", "cancelled"]


# ============================================================================
# Request
# ============================================================================


class LiveSessionCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=500)
    description: str | None = None

    course_id: int | None = None
    lesson_id: int | None = None
    organization_id: int | None = None  # Single-tenant XIU: avto-fill

    scheduled_start: datetime
    scheduled_end: datetime
    duration_minutes: int = Field(default=60, ge=5, le=600)

    provider: LiveProvider = "native"
    is_recording_enabled: bool = False
    min_attendance_percent: int = Field(default=75, ge=0, le=100)
    requires_approval: bool = False

    @model_validator(mode="after")
    def _check_dates(self) -> "LiveSessionCreateRequest":
        if self.scheduled_end <= self.scheduled_start:
            raise ValueError("scheduled_end scheduled_start dan keyin bo'lishi shart")
        return self


class LiveSessionUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=500)
    description: str | None = None

    course_id: int | None = None
    lesson_id: int | None = None

    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=5, le=600)

    provider: LiveProvider | None = None
    is_recording_enabled: bool | None = None
    min_attendance_percent: int | None = Field(default=None, ge=0, le=100)
    requires_approval: bool | None = None

    @model_validator(mode="after")
    def _check_dates(self) -> "LiveSessionUpdateRequest":
        if (
            self.scheduled_start is not None
            and self.scheduled_end is not None
            and self.scheduled_end <= self.scheduled_start
        ):
            raise ValueError("scheduled_end scheduled_start dan keyin bo'lishi shart")
        return self


# ============================================================================
# Response
# ============================================================================


class LiveSessionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int | None
    course_id: int | None
    lesson_id: int | None

    title: str
    description: str | None

    scheduled_start: datetime
    scheduled_end: datetime
    duration_minutes: int

    provider: str
    provider_meeting_id: str | None
    provider_metadata: dict

    host_user_id: int
    host_full_name: str | None = None  # javobda to'ldiriladi
    status: str
    actual_start: datetime | None
    actual_end: datetime | None

    is_recording_enabled: bool
    recording_url: str | None
    thumbnail_url: str | None
    recording_size_bytes: int | None
    recording_duration_seconds: int | None
    recording_mime_type: str | None
    min_attendance_percent: int
    requires_approval: bool = False

    created_at: datetime
    updated_at: datetime


class PaginatedLiveSessions(BaseModel):
    items: list[LiveSessionPublic]
    total: int


class LiveAttendancePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    user_id: int
    joined_at: datetime | None
    left_at: datetime | None
    total_minutes: int
    is_counted: bool


class LiveAttendanceItem(BaseModel):
    """Davomat ro'yxati uchun — user metadata bilan birga."""

    user_id: int
    full_name: str
    email: str
    joined_at: datetime | None
    left_at: datetime | None
    total_minutes: int
    live_minutes: int  # ulanib turgan bo'lsa o'tgan vaqtni ham qo'shadi
    is_counted: bool


class LiveAdmissionItem(BaseModel):
    """Waiting room — kutayotgan talaba (host ko'radi)."""

    user_id: int
    full_name: str
    email: str | None
    status: str
    requested_at: datetime


class LiveAdmissionDecision(BaseModel):
    approve: bool


class AttendanceSummary(BaseModel):
    session_id: int
    status: str
    duration_minutes: int
    min_attendance_percent: int
    total_participants: int
    joined_participants: int
    counted_participants: int
    counted_percent: float
    average_minutes: float


class CalendarTokenResponse(BaseModel):
    """Shaxsiy iCal URL — kalendar app'iga subscribe qilish uchun."""

    url: str
    token: str


class LiveJoinInfo(BaseModel):
    """Live sessionga qo'shilish uchun client'ga qaytadigan ma'lumot.

    Provider-agnostic shape:
      - join_url: brauzerda ochiladigan URL (Jitsi'da JWT bilan)
      - embed_token: frontend SDK init uchun (Jitsi JWT, Zoom signature, ...)
      - embed_config: provider-spec config (domain, options)
    """

    session_id: int
    provider: str
    room_name: str
    join_url: str
    is_host: bool
    embed_token: str | None = None
    embed_config: dict | None = None
    pending: bool = False  # waiting room — host tasdig'i kutilmoqda


# Phase 7a — LiveRecording
class LiveRecordingPublic(BaseModel):
    id: int
    session_id: int
    recorded_by: int | None
    status: str
    object_key: str | None
    url: str | None
    mime_type: str
    started_at: datetime
    finalized_at: datetime | None
    duration_seconds: int | None
    file_size_bytes: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Phase 9c — Captions
class LiveCaptionItem(BaseModel):
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    text: str = Field(min_length=1, max_length=2000)
    lang: str = Field(default="uz", max_length=10)


class LiveCaptionBatchRequest(BaseModel):
    items: list[LiveCaptionItem] = Field(min_length=1, max_length=200)


class LiveCaptionPublic(BaseModel):
    id: int
    session_id: int
    speaker_user_id: int | None
    start_ms: int
    end_ms: int
    text: str
    lang: str

    model_config = ConfigDict(from_attributes=True)

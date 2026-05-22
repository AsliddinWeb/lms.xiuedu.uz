"""SCORM Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScormPackagePublic(BaseModel):
    id: int
    content_item_id: int
    version: str
    manifest_identifier: str | None
    title: str | None
    description: str | None
    launch_url: str
    package_path: str
    file_size: int | None
    mastery_score: Decimal | None
    uploaded_at: datetime
    # Full URL — public access (frontend iframe src uchun)
    launch_full_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ScormAttemptPublic(BaseModel):
    id: int
    user_id: int
    package_id: int
    lesson_id: int | None
    attempt_number: int
    status: str
    cmi_data: dict[str, Any]
    score_raw: Decimal | None
    score_min: Decimal | None
    score_max: Decimal | None
    total_time: str | None
    session_time: str | None
    bookmark: str | None
    suspend_data: str | None
    started_at: datetime
    completed_at: datetime | None
    last_accessed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CmiCommitRequest(BaseModel):
    """SCORM `LMSCommit` payload — batch'da bir nechta SetValue chaqiruv natijasi."""

    cmi_updates: dict[str, Any] = Field(default_factory=dict)


class StartAttemptResponse(BaseModel):
    """SCORM player iframe ishga tushishi uchun zarur ma'lumotlar."""

    attempt: ScormAttemptPublic
    package: ScormPackagePublic
    launch_full_url: str

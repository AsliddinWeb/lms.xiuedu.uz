"""Content Pydantic schemalari (Phase 3a)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

ContentType = Literal["text", "video", "pdf", "file", "link"]
ContentStatus = Literal["draft", "review", "published", "archived"]
LanguageCode = Literal["uz-lat", "uz-cyr", "ru", "en"]


class ContentCreateRequest(BaseModel):
    type: ContentType
    title: str = Field(min_length=2, max_length=255)
    description: str | None = None
    subject_id: int | None = None

    file_url: str | None = Field(default=None, max_length=2048)
    mime_type: str | None = Field(default=None, max_length=100)
    file_size: int | None = Field(default=None, ge=0)
    duration_seconds: int | None = Field(default=None, ge=0)

    content_data: dict[str, Any] = Field(default_factory=dict)
    language: LanguageCode = "uz-lat"
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_payload(self) -> "ContentCreateRequest":
        if self.type == "link":
            if not self.file_url:
                raise ValueError("link type uchun file_url majburiy")
            # URL bo'lishi kerak
            try:
                HttpUrl(self.file_url)
            except Exception as exc:  # noqa: BLE001
                raise ValueError("file_url to'g'ri URL bo'lishi kerak") from exc
        if self.type == "text" and not self.content_data:
            raise ValueError("text type uchun content_data majburiy (rich-text JSON)")
        # Tag uzunligi
        for t in self.tags:
            if len(t) > 50:
                raise ValueError(f"Tag uzunligi 50 belgidan oshmasligi kerak: {t!r}")
        return self


class ContentUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    subject_id: int | None = None

    file_url: str | None = Field(default=None, max_length=2048)
    mime_type: str | None = Field(default=None, max_length=100)
    file_size: int | None = Field(default=None, ge=0)
    duration_seconds: int | None = Field(default=None, ge=0)

    content_data: dict[str, Any] | None = None
    language: LanguageCode | None = None
    tags: list[str] | None = None


class ContentPublic(BaseModel):
    id: int
    type: str
    title: str
    description: str | None
    subject_id: int | None
    author_id: int

    file_url: str | None
    mime_type: str | None
    file_size: int | None
    duration_seconds: int | None

    content_data: dict[str, Any]
    language: str
    tags: list[str]

    version: int
    parent_id: int | None
    status: str
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedContent(BaseModel):
    items: list[ContentPublic]
    total: int


class ContentUploadResponse(BaseModel):
    """`/content/{id}/upload` endpoint javobi."""

    id: int
    file_url: str
    mime_type: str
    file_size: int

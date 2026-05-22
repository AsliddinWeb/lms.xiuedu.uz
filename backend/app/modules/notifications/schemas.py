"""Notification Pydantic schemalari — Phase 7d."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationPublic(BaseModel):
    id: int
    user_id: int
    event_type: str
    title: str
    body: str | None
    action_url: str | None
    data: dict | None = None
    read_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedNotifications(BaseModel):
    items: list[NotificationPublic]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    count: int


class MarkAllReadResponse(BaseModel):
    marked: int

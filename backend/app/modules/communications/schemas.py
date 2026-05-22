"""Communications Pydantic schemas — chat + forum."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# Chat — Conversation
# ============================================================================

ConversationType = Literal["direct", "group", "course"]


class ConversationMemberPublic(BaseModel):
    user_id: int
    role: str
    joined_at: datetime
    last_read_at: datetime | None
    is_muted: bool

    model_config = ConfigDict(from_attributes=True)


class ConversationPublic(BaseModel):
    id: int
    type: ConversationType
    title: str | None
    course_id: int | None
    created_by: int | None
    last_message_at: datetime | None
    is_archived: bool
    created_at: datetime
    # Server-computed, optional context fields
    unread_count: int = 0
    last_message_preview: str | None = None
    member_ids: list[int] = Field(default_factory=list)
    # Phase 13.21 — member_id => full_name xaritasi
    member_names: dict[int, str] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class ConversationCreateDirect(BaseModel):
    """1:1 chat boshlash — peer_user_id bilan."""

    peer_user_id: int = Field(..., gt=0)


class ConversationCreateGroup(BaseModel):
    """Guruh chat — kamida 2 a'zo (+ yaratuvchi)."""

    title: str = Field(..., min_length=1, max_length=255)
    member_ids: list[int] = Field(..., min_length=1)
    course_id: int | None = None


class ConversationMemberAdd(BaseModel):
    user_ids: list[int] = Field(..., min_length=1)


# ============================================================================
# Chat — Message
# ============================================================================


class MessagePublic(BaseModel):
    id: int
    conversation_id: int
    sender_id: int | None
    sender_name: str | None = None  # Phase 13.21
    body: str | None
    attachment_url: str | None
    attachment_mime: str | None
    attachment_size: int | None
    reply_to_id: int | None
    edited_at: datetime | None
    deleted_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageCreate(BaseModel):
    body: str | None = Field(None, max_length=10_000)
    attachment_url: str | None = None
    attachment_mime: str | None = Field(None, max_length=100)
    attachment_size: int | None = Field(None, ge=0)
    reply_to_id: int | None = Field(None, gt=0)


class MessageEdit(BaseModel):
    body: str = Field(..., min_length=1, max_length=10_000)


class ConversationReadMark(BaseModel):
    """`last_read_at` ni hozirgi vaqtga yoki ko'rsatilgan vaqtga o'rnatadi."""

    last_message_id: int | None = None


# ============================================================================
# Forum — Thread + Post
# ============================================================================


class ForumThreadPublic(BaseModel):
    id: int
    course_id: int
    lesson_id: int | None
    author_id: int | None
    author_name: str | None = None  # Phase 13.22 — full_name'dan resolve
    title: str
    body: str | None
    is_pinned: bool
    is_locked: bool
    is_announcement: bool
    view_count: int
    post_count: int
    last_reply_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ForumThreadCreate(BaseModel):
    course_id: int = Field(..., gt=0)
    lesson_id: int | None = Field(None, gt=0)
    title: str = Field(..., min_length=1, max_length=500)
    body: str | None = Field(None, max_length=20_000)
    is_announcement: bool = False


class ForumThreadUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=500)
    body: str | None = Field(None, max_length=20_000)
    is_pinned: bool | None = None
    is_locked: bool | None = None


class ForumPostPublic(BaseModel):
    id: int
    thread_id: int
    author_id: int | None
    author_name: str | None = None  # Phase 13.22
    body: str
    parent_post_id: int | None
    like_count: int
    edited_at: datetime | None
    deleted_at: datetime | None
    created_at: datetime
    liked_by_me: bool = False

    model_config = ConfigDict(from_attributes=True)


class ForumPostCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=20_000)
    parent_post_id: int | None = Field(None, gt=0)


class ForumPostEdit(BaseModel):
    body: str = Field(..., min_length=1, max_length=20_000)


# ============================================================================
# Lesson comments (Phase 11c)
# ============================================================================


class LessonCommentPublic(BaseModel):
    id: int
    lesson_id: int
    author_id: int | None
    author_name: str | None = None  # Phase 13.16
    body: str
    parent_comment_id: int | None
    like_count: int
    edited_at: datetime | None
    deleted_at: datetime | None
    created_at: datetime
    liked_by_me: bool = False

    model_config = ConfigDict(from_attributes=True)


class LessonCommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=10_000)
    parent_comment_id: int | None = Field(None, gt=0)


class LessonCommentEdit(BaseModel):
    body: str = Field(..., min_length=1, max_length=10_000)


# ============================================================================
# WebSocket payloads
# ============================================================================


class WsChatEvent(BaseModel):
    """Server -> client event over WebSocket."""

    type: Literal[
        "message.new",
        "message.edit",
        "message.delete",
        "conversation.read",
        "typing",
        "presence",
    ]
    conversation_id: int
    payload: dict

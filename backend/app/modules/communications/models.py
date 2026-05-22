"""Chat + Forum models — Phase 11b."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IDMixin, TimestampMixin


# ============================================================================
# Chat
# ============================================================================


class Conversation(Base, IDMixin, TimestampMixin):
    """Chat container.

    `type` qiymatlari:
        'direct' — 1:1 ikki user orasida
        'group'  — 3+ user, qo'lda yaratilgan
        'course' — kurs-darajasidagi auto-yaratilgan chat (course_id bilan)
    """

    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_last_msg", text("last_message_at DESC")),
    )

    type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    course_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("courses.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    created_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    members: Mapped[list["ConversationMember"]] = relationship(
        "ConversationMember",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} type={self.type} title={self.title!r}>"


class ConversationMember(Base):
    """Kim chatda qatnashadi + last_read_at."""

    __tablename__ = "conversation_members"
    __table_args__ = (
        Index("ix_conv_members_user", "user_id"),
    )

    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # 'member' | 'admin' (group/course chatda admin xabarlarni o'chira oladi)
    role: Mapped[str] = mapped_column(String(20), default="member", nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    last_read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_muted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    conversation: Mapped[Conversation] = relationship(
        "Conversation", back_populates="members"
    )

    def __repr__(self) -> str:
        return (
            f"<ConversationMember conv={self.conversation_id} user={self.user_id}>"
        )


class Message(Base, IDMixin):
    """Chat xabari."""

    __tablename__ = "messages"
    __table_args__ = (
        Index(
            "ix_messages_conv_created",
            "conversation_id",
            text("created_at DESC"),
        ),
    )

    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    sender_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachment_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachment_mime: Mapped[str | None] = mapped_column(String(100), nullable=True)
    attachment_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    reply_to_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    conversation: Mapped[Conversation] = relationship(
        "Conversation", back_populates="messages"
    )

    def __repr__(self) -> str:
        return (
            f"<Message id={self.id} conv={self.conversation_id} sender={self.sender_id}>"
        )


# ============================================================================
# Forum (course-scoped)
# ============================================================================


class ForumThread(Base, IDMixin, TimestampMixin):
    """Kurs ichidagi muhokama mavzu (yoki announcement).

    `is_announcement=True` bo'lsa, pedagog/admin tomonidan yaratiladi va
    talabalar javob bera olmaydi (faqat o'qiydilar).
    """

    __tablename__ = "forum_threads"
    __table_args__ = (
        Index(
            "ix_forum_threads_course_feed",
            "course_id",
            text("is_pinned DESC"),
            text("last_reply_at DESC"),
        ),
    )

    course_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("courses.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    lesson_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("lessons.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    author_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_announcement: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    post_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_reply_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    posts: Mapped[list["ForumPost"]] = relationship(
        "ForumPost",
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="ForumPost.created_at",
    )

    def __repr__(self) -> str:
        return f"<ForumThread id={self.id} title={self.title!r}>"


class ForumPost(Base, IDMixin):
    """Mavzu ichidagi javob. Nested replies — `parent_post_id`."""

    __tablename__ = "forum_posts"
    __table_args__ = (
        Index("ix_forum_posts_thread_created", "thread_id", "created_at"),
    )

    thread_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("forum_threads.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    author_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    parent_post_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("forum_posts.id", ondelete="SET NULL"),
        nullable=True,
    )
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    thread: Mapped[ForumThread] = relationship("ForumThread", back_populates="posts")

    def __repr__(self) -> str:
        return f"<ForumPost id={self.id} thread={self.thread_id}>"


class ForumPostLike(Base):
    """Forum post likes — (post_id, user_id) junction."""

    __tablename__ = "forum_post_likes"

    post_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("forum_posts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<ForumPostLike post={self.post_id} user={self.user_id}>"


# ============================================================================
# Lesson comments (Phase 11c)
# ============================================================================


class LessonComment(Base, IDMixin):
    """Dars sahifasidagi izohlar — 1 darajali reply (parent_comment_id)."""

    __tablename__ = "lesson_comments"
    __table_args__ = (
        Index(
            "ix_lesson_comments_lesson_created",
            "lesson_id",
            text("created_at DESC"),
        ),
    )

    lesson_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("lessons.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    author_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    parent_comment_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("lesson_comments.id", ondelete="SET NULL"),
        nullable=True,
    )
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<LessonComment id={self.id} lesson={self.lesson_id}>"


class LessonCommentLike(Base):
    """Lesson comment like junction."""

    __tablename__ = "lesson_comment_likes"

    comment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("lesson_comments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<LessonCommentLike comment={self.comment_id} user={self.user_id}>"

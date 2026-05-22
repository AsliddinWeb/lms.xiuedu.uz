"""phase11b_communications

Revision ID: c2e850ab0653
Revises: c59a86dafd16
Create Date: 2026-05-21 15:00:00.000000

Phase 11b — Communications (chat + forum).

Yangi jadvallar:
    Chat (1:1 va guruh xabar almashish):
        conversations           — chat container (direct/group, optional course-scope)
        conversation_members    — kim qatnashadi + last_read_at
        messages                — xabar matni + attachment + reply_to

    Forum (course-scoped muhokama):
        forum_threads           — mavzu (course/lesson scope)
        forum_posts             — mavzu ichidagi javoblar (nested via parent_post_id)
        forum_post_likes        — like junction
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "c2e850ab0653"
down_revision: str | None = "c59a86dafd16"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ========================================================================
    # CHAT
    # ========================================================================

    op.create_table(
        "conversations",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        # 'direct' (1:1) | 'group' (3+) | 'course' (course-wide auto-created)
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column(
            "course_id",
            sa.BigInteger(),
            sa.ForeignKey("courses.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "created_by",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "last_message_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_conversations_last_msg",
        "conversations",
        [sa.text("last_message_at DESC")],
    )

    op.create_table(
        "conversation_members",
        sa.Column(
            "conversation_id",
            sa.BigInteger(),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        # 'member' | 'admin'
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_muted", sa.Boolean(), nullable=False, server_default="false"),
    )
    # User'ning chatlar ro'yxati
    op.create_index(
        "ix_conv_members_user", "conversation_members", ["user_id"]
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.BigInteger(),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "sender_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("attachment_url", sa.Text(), nullable=True),
        sa.Column("attachment_mime", sa.String(100), nullable=True),
        sa.Column("attachment_size", sa.BigInteger(), nullable=True),
        # Threading — null bo'lsa top-level
        sa.Column(
            "reply_to_id",
            sa.BigInteger(),
            sa.ForeignKey("messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    # Paginated history lookup
    op.create_index(
        "ix_messages_conv_created",
        "messages",
        ["conversation_id", sa.text("created_at DESC")],
    )

    # ========================================================================
    # FORUM
    # ========================================================================

    op.create_table(
        "forum_threads",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "course_id",
            sa.BigInteger(),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "lesson_id",
            sa.BigInteger(),
            sa.ForeignKey("lessons.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "author_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "is_announcement", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "view_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "post_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("last_reply_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    # Course feed: pinned avval, keyin last_reply_at desc
    op.create_index(
        "ix_forum_threads_course_feed",
        "forum_threads",
        ["course_id", sa.text("is_pinned DESC"), sa.text("last_reply_at DESC")],
    )

    op.create_table(
        "forum_posts",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "thread_id",
            sa.BigInteger(),
            sa.ForeignKey("forum_threads.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "author_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        # Nested reply (null = thread root reply)
        sa.Column(
            "parent_post_id",
            sa.BigInteger(),
            sa.ForeignKey("forum_posts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("like_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_forum_posts_thread_created",
        "forum_posts",
        ["thread_id", "created_at"],
    )

    op.create_table(
        "forum_post_likes",
        sa.Column(
            "post_id",
            sa.BigInteger(),
            sa.ForeignKey("forum_posts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("forum_post_likes")
    op.drop_index("ix_forum_posts_thread_created", table_name="forum_posts")
    op.drop_table("forum_posts")
    op.drop_index("ix_forum_threads_course_feed", table_name="forum_threads")
    op.drop_table("forum_threads")
    op.drop_index("ix_messages_conv_created", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conv_members_user", table_name="conversation_members")
    op.drop_table("conversation_members")
    op.drop_index("ix_conversations_last_msg", table_name="conversations")
    op.drop_table("conversations")

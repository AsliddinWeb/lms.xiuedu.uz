"""Chat service — Phase 11b.

Conversation CRUD + member management + message ops.
Direct/group/course chat turlarini boshqaradi.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.modules.communications.models import (
    Conversation,
    ConversationMember,
    Message,
)


def _now() -> datetime:
    return datetime.now(UTC)


# ============================================================================
# Membership checks
# ============================================================================


async def assert_member(
    db: AsyncSession, conversation_id: int, user_id: int
) -> ConversationMember:
    """User chatda bo'lmasa 403."""
    cm = await db.get(ConversationMember, (conversation_id, user_id))
    if cm is None:
        raise ForbiddenError("Bu chatga kirish ruxsati yo'q")
    return cm


async def is_member(
    db: AsyncSession, conversation_id: int, user_id: int
) -> bool:
    return (await db.get(ConversationMember, (conversation_id, user_id))) is not None


# ============================================================================
# Conversation creation
# ============================================================================


async def get_or_create_direct(
    db: AsyncSession, user_a_id: int, peer_user_id: int
) -> Conversation:
    """1:1 chat — agar bor bo'lsa qaytaradi, yo'q bo'lsa yaratadi."""
    if user_a_id == peer_user_id:
        raise ForbiddenError("O'zingiz bilan chat ocha olmaysiz")

    # Mavjud direct chatni qidirish: 2 ta member, ikkalovi ham ro'yxatda
    cm_a = ConversationMember.__table__.alias("cm_a")
    cm_b = ConversationMember.__table__.alias("cm_b")
    stmt = (
        select(Conversation.id)
        .join(cm_a, cm_a.c.conversation_id == Conversation.id)
        .join(cm_b, cm_b.c.conversation_id == Conversation.id)
        .where(
            Conversation.type == "direct",
            cm_a.c.user_id == user_a_id,
            cm_b.c.user_id == peer_user_id,
        )
        .limit(1)
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        return await db.get(Conversation, existing)  # type: ignore[return-value]

    conv = Conversation(type="direct", created_by=user_a_id)
    db.add(conv)
    await db.flush()
    db.add_all(
        [
            ConversationMember(conversation_id=conv.id, user_id=user_a_id, role="member"),
            ConversationMember(
                conversation_id=conv.id, user_id=peer_user_id, role="member"
            ),
        ]
    )
    await db.flush()
    return conv


async def create_group(
    db: AsyncSession,
    *,
    creator_id: int,
    title: str,
    member_ids: list[int],
    course_id: int | None = None,
) -> Conversation:
    unique_member_ids = list({creator_id, *member_ids})
    if len(unique_member_ids) < 2:
        raise ForbiddenError("Guruh chat uchun kamida 2 a'zo kerak")

    conv = Conversation(
        type="course" if course_id is not None else "group",
        title=title,
        course_id=course_id,
        created_by=creator_id,
    )
    db.add(conv)
    await db.flush()

    rows = [
        ConversationMember(
            conversation_id=conv.id,
            user_id=uid,
            role="admin" if uid == creator_id else "member",
        )
        for uid in unique_member_ids
    ]
    db.add_all(rows)
    await db.flush()
    return conv


# ============================================================================
# Conversation listing + read state
# ============================================================================


async def list_for_user(
    db: AsyncSession,
    user_id: int,
    *,
    include_archived: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Conversation], int]:
    base = (
        select(Conversation)
        .join(
            ConversationMember,
            ConversationMember.conversation_id == Conversation.id,
        )
        .where(ConversationMember.user_id == user_id)
    )
    if not include_archived:
        base = base.where(Conversation.is_archived.is_(False))

    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()

    stmt = (
        base.order_by(
            Conversation.last_message_at.desc().nullslast(),
            Conversation.created_at.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await db.execute(stmt)).scalars().all()
    return list(items), int(total)


async def get_member_ids(db: AsyncSession, conversation_id: int) -> list[int]:
    rows = (
        await db.execute(
            select(ConversationMember.user_id).where(
                ConversationMember.conversation_id == conversation_id
            )
        )
    ).scalars().all()
    return list(rows)


async def unread_count(
    db: AsyncSession, conversation_id: int, user_id: int
) -> int:
    cm = await db.get(ConversationMember, (conversation_id, user_id))
    if cm is None:
        return 0
    cutoff = cm.last_read_at
    stmt = select(func.count(Message.id)).where(
        Message.conversation_id == conversation_id,
        Message.deleted_at.is_(None),
        Message.sender_id != user_id,
    )
    if cutoff is not None:
        stmt = stmt.where(Message.created_at > cutoff)
    return int((await db.execute(stmt)).scalar_one())


async def last_message(
    db: AsyncSession, conversation_id: int
) -> Message | None:
    stmt = (
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.deleted_at.is_(None),
        )
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def mark_read(
    db: AsyncSession,
    conversation_id: int,
    user_id: int,
    *,
    at: datetime | None = None,
) -> ConversationMember:
    cm = await assert_member(db, conversation_id, user_id)
    cm.last_read_at = at or _now()
    await db.flush()
    return cm


# ============================================================================
# Member management
# ============================================================================


async def add_members(
    db: AsyncSession,
    conversation_id: int,
    actor_id: int,
    user_ids: list[int],
) -> int:
    """Faqat admin yangi a'zo qo'sha oladi (group/course)."""
    cm = await assert_member(db, conversation_id, actor_id)
    conv = await db.get(Conversation, conversation_id)
    if conv is None:
        raise NotFoundError("Chat topilmadi")
    if conv.type == "direct":
        raise ForbiddenError("Direct chatga a'zo qo'shib bo'lmaydi")
    if cm.role != "admin":
        raise ForbiddenError("Faqat admin a'zo qo'sha oladi")

    existing = set(await get_member_ids(db, conversation_id))
    new_ids = [uid for uid in user_ids if uid not in existing]
    if not new_ids:
        return 0
    db.add_all(
        [
            ConversationMember(conversation_id=conversation_id, user_id=uid)
            for uid in new_ids
        ]
    )
    await db.flush()
    return len(new_ids)


async def remove_member(
    db: AsyncSession,
    conversation_id: int,
    actor_id: int,
    target_user_id: int,
) -> None:
    """Admin har kimni, oddiy member faqat o'zini chiqarib oladi."""
    actor_cm = await assert_member(db, conversation_id, actor_id)
    conv = await db.get(Conversation, conversation_id)
    if conv is None:
        raise NotFoundError("Chat topilmadi")
    if conv.type == "direct":
        raise ForbiddenError("Direct chatdan a'zoni olib bo'lmaydi")

    if actor_id != target_user_id and actor_cm.role != "admin":
        raise ForbiddenError("Faqat admin boshqa a'zoni chiqara oladi")

    target = await db.get(ConversationMember, (conversation_id, target_user_id))
    if target is None:
        raise NotFoundError("A'zo topilmadi")
    await db.delete(target)
    await db.flush()


# ============================================================================
# Messages
# ============================================================================


async def send_message(
    db: AsyncSession,
    *,
    conversation_id: int,
    sender_id: int,
    body: str | None,
    attachment_url: str | None = None,
    attachment_mime: str | None = None,
    attachment_size: int | None = None,
    reply_to_id: int | None = None,
) -> Message:
    if not body and not attachment_url:
        raise ForbiddenError("Bo'sh xabar yuborib bo'lmaydi")
    await assert_member(db, conversation_id, sender_id)

    if reply_to_id is not None:
        target = await db.get(Message, reply_to_id)
        if target is None or target.conversation_id != conversation_id:
            raise NotFoundError("Reply uchun xabar topilmadi")

    msg = Message(
        conversation_id=conversation_id,
        sender_id=sender_id,
        body=body,
        attachment_url=attachment_url,
        attachment_mime=attachment_mime,
        attachment_size=attachment_size,
        reply_to_id=reply_to_id,
    )
    db.add(msg)
    await db.flush()

    conv = await db.get(Conversation, conversation_id)
    if conv is not None:
        conv.last_message_at = msg.created_at
        await db.flush()
    return msg


async def list_messages(
    db: AsyncSession,
    conversation_id: int,
    user_id: int,
    *,
    before_id: int | None = None,
    limit: int = 50,
) -> list[Message]:
    await assert_member(db, conversation_id, user_id)
    stmt = (
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
        )
        .order_by(Message.created_at.desc())
        .limit(min(limit, 200))
    )
    if before_id is not None:
        stmt = stmt.where(Message.id < before_id)
    rows = (await db.execute(stmt)).scalars().all()
    # Frontend ascending kutadi
    return list(reversed(rows))


async def edit_message(
    db: AsyncSession, message_id: int, user_id: int, new_body: str
) -> Message:
    msg = await db.get(Message, message_id)
    if msg is None or msg.deleted_at is not None:
        raise NotFoundError("Xabar topilmadi")
    if msg.sender_id != user_id:
        raise ForbiddenError("Faqat egasi tahrirlay oladi")
    msg.body = new_body
    msg.edited_at = _now()
    await db.flush()
    return msg


async def delete_message(
    db: AsyncSession, message_id: int, user_id: int
) -> Message:
    """Soft delete — egasi yoki chat admini o'chirsa bo'ladi."""
    msg = await db.get(Message, message_id)
    if msg is None or msg.deleted_at is not None:
        raise NotFoundError("Xabar topilmadi")
    if msg.sender_id != user_id:
        actor_cm = await db.get(
            ConversationMember, (msg.conversation_id, user_id)
        )
        if actor_cm is None or actor_cm.role != "admin":
            raise ForbiddenError("O'chirish ruxsati yo'q")
    msg.deleted_at = _now()
    msg.body = None
    await db.flush()
    return msg


# ============================================================================
# Helpers for course-scoped auto-chat
# ============================================================================


async def ensure_course_chat(
    db: AsyncSession, course_id: int, member_ids: list[int], title: str
) -> Conversation:
    """Kurs uchun yagona course-chat ni topadi yoki yaratadi va a'zolar setini sinxronlaydi."""
    existing = (
        await db.execute(
            select(Conversation).where(
                Conversation.type == "course",
                Conversation.course_id == course_id,
            )
        )
    ).scalar_one_or_none()

    if existing is None:
        conv = Conversation(type="course", title=title, course_id=course_id)
        db.add(conv)
        await db.flush()
    else:
        conv = existing

    existing_ids = set(await get_member_ids(db, conv.id))
    new_ids = [uid for uid in member_ids if uid not in existing_ids]
    if new_ids:
        db.add_all(
            [
                ConversationMember(conversation_id=conv.id, user_id=uid)
                for uid in new_ids
            ]
        )
        await db.flush()
    return conv

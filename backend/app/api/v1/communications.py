"""Communications endpoints — Phase 11b.

Chat (REST + WebSocket) va forum (REST) endpointlari.
"""

from __future__ import annotations

from fastapi import (
    APIRouter,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.security import decode_token
from app.modules.auth.dependencies import CurrentUser, DbSession
from app.modules.communications import chat_service, comments_service, forum_service
from app.modules.notifications import service as notifications_service
from app.modules.communications.schemas import (
    ConversationCreateDirect,
    ConversationCreateGroup,
    ConversationMemberAdd,
    ConversationPublic,
    ConversationReadMark,
    ForumPostCreate,
    ForumPostEdit,
    ForumPostPublic,
    ForumThreadCreate,
    ForumThreadPublic,
    ForumThreadUpdate,
    LessonCommentCreate,
    LessonCommentEdit,
    LessonCommentPublic,
    MessageCreate,
    MessageEdit,
    MessagePublic,
)
from app.modules.communications.ws_manager import manager as ws_manager
from app.modules.users.models import User
from sqlalchemy import select as _select

router = APIRouter()


# ============================================================================
# Helpers
# ============================================================================


async def _serialize_conversation(
    db: AsyncSession, conv, user_id: int
) -> ConversationPublic:
    member_ids = await chat_service.get_member_ids(db, conv.id)
    unread = await chat_service.unread_count(db, conv.id, user_id)
    last = await chat_service.last_message(db, conv.id)
    preview = last.body if last and last.body else None
    # Phase 13.21 — member full_name xaritasi
    names = await _resolve_author_names(db, list(member_ids))
    return ConversationPublic(
        id=conv.id,
        type=conv.type,
        title=conv.title,
        course_id=conv.course_id,
        created_by=conv.created_by,
        last_message_at=conv.last_message_at,
        is_archived=conv.is_archived,
        created_at=conv.created_at,
        unread_count=unread,
        last_message_preview=preview,
        member_ids=member_ids,
        member_names=names,
    )


class PaginatedConversations(BaseModel):
    items: list[ConversationPublic]
    total: int


class ContactPublic(BaseModel):
    """Suhbatlasha olinadigan kontakt (o'qituvchi / kursdosh) — Phase 26."""

    user_id: int
    full_name: str
    avatar_url: str | None = None
    relation: str  # 'teacher' | 'classmate'


class PaginatedMessages(BaseModel):
    items: list[MessagePublic]
    has_more: bool


class PaginatedThreads(BaseModel):
    items: list[ForumThreadPublic]
    total: int


class PaginatedPosts(BaseModel):
    items: list[ForumPostPublic]
    total: int


class PaginatedComments(BaseModel):
    items: list[LessonCommentPublic]
    total: int


# Phase 13.16/13.22 — author_id => full_name batch resolver
async def _resolve_author_names(
    db: AsyncSession, author_ids: list[int | None]
) -> dict[int, str]:
    ids = {a for a in author_ids if a is not None}
    if not ids:
        return {}
    rows = (
        await db.execute(_select(User.id, User.full_name).where(User.id.in_(ids)))
    ).all()
    return {uid: name for uid, name in rows}


# ============================================================================
# Chat — conversations
# ============================================================================


@router.get(
    "/chat/conversations",
    response_model=PaginatedConversations,
    tags=["chat"],
)
async def list_conversations(
    db: DbSession,
    user: CurrentUser,
    include_archived: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> PaginatedConversations:
    items, total = await chat_service.list_for_user(
        db,
        user.id,
        include_archived=include_archived,
        page=page,
        page_size=page_size,
    )
    return PaginatedConversations(
        items=[await _serialize_conversation(db, c, user.id) for c in items],
        total=total,
    )


@router.post(
    "/chat/conversations/direct",
    response_model=ConversationPublic,
    status_code=status.HTTP_201_CREATED,
    tags=["chat"],
)
async def open_direct_conversation(
    payload: ConversationCreateDirect,
    db: DbSession,
    user: CurrentUser,
) -> ConversationPublic:
    conv = await chat_service.get_or_create_direct(db, user.id, payload.peer_user_id)
    await db.commit()
    await db.refresh(conv)
    return await _serialize_conversation(db, conv, user.id)


@router.get("/chat/contacts", response_model=list[ContactPublic], tags=["chat"])
async def list_contacts(
    db: DbSession,
    user: CurrentUser,
) -> list[ContactPublic]:
    rows = await chat_service.get_contacts(db, user.id)
    return [ContactPublic(**r) for r in rows]


@router.post(
    "/chat/conversations/group",
    response_model=ConversationPublic,
    status_code=status.HTTP_201_CREATED,
    tags=["chat"],
)
async def create_group_conversation(
    payload: ConversationCreateGroup,
    db: DbSession,
    user: CurrentUser,
) -> ConversationPublic:
    conv = await chat_service.create_group(
        db,
        creator_id=user.id,
        title=payload.title,
        member_ids=payload.member_ids,
        course_id=payload.course_id,
    )
    await db.commit()
    await db.refresh(conv)
    return await _serialize_conversation(db, conv, user.id)


@router.get(
    "/chat/conversations/{conversation_id}",
    response_model=ConversationPublic,
    tags=["chat"],
)
async def get_conversation(
    conversation_id: int,
    db: DbSession,
    user: CurrentUser,
) -> ConversationPublic:
    await chat_service.assert_member(db, conversation_id, user.id)
    from app.modules.communications.models import Conversation

    conv = await db.get(Conversation, conversation_id)
    if conv is None:
        raise NotFoundError("Chat topilmadi")
    return await _serialize_conversation(db, conv, user.id)


@router.post(
    "/chat/conversations/{conversation_id}/members",
    response_model=ConversationPublic,
    tags=["chat"],
)
async def add_conversation_members(
    conversation_id: int,
    payload: ConversationMemberAdd,
    db: DbSession,
    user: CurrentUser,
) -> ConversationPublic:
    await chat_service.add_members(db, conversation_id, user.id, payload.user_ids)
    await db.commit()
    from app.modules.communications.models import Conversation

    conv = await db.get(Conversation, conversation_id)
    return await _serialize_conversation(db, conv, user.id)


@router.delete(
    "/chat/conversations/{conversation_id}/members/{target_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["chat"],
)
async def remove_conversation_member(
    conversation_id: int,
    target_user_id: int,
    db: DbSession,
    user: CurrentUser,
) -> None:
    await chat_service.remove_member(
        db, conversation_id, user.id, target_user_id
    )
    await db.commit()


@router.post(
    "/chat/conversations/{conversation_id}/read",
    response_model=ConversationPublic,
    tags=["chat"],
)
async def mark_conversation_read(
    conversation_id: int,
    payload: ConversationReadMark,  # noqa: ARG001 — reserved for future per-message marker
    db: DbSession,
    user: CurrentUser,
) -> ConversationPublic:
    await chat_service.mark_read(db, conversation_id, user.id)
    await db.commit()
    # Other members get a read receipt
    member_ids = await chat_service.get_member_ids(db, conversation_id)
    targets = [uid for uid in member_ids if uid != user.id]
    if targets:
        await ws_manager.publish_to_users(
            targets,
            {
                "type": "conversation.read",
                "conversation_id": conversation_id,
                "payload": {"user_id": user.id},
            },
        )
    from app.modules.communications.models import Conversation

    conv = await db.get(Conversation, conversation_id)
    return await _serialize_conversation(db, conv, user.id)


# ============================================================================
# Chat — messages
# ============================================================================


@router.get(
    "/chat/conversations/{conversation_id}/messages",
    response_model=PaginatedMessages,
    tags=["chat"],
)
async def list_messages(
    conversation_id: int,
    db: DbSession,
    user: CurrentUser,
    before_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> PaginatedMessages:
    items = await chat_service.list_messages(
        db, conversation_id, user.id, before_id=before_id, limit=limit
    )
    has_more = len(items) == limit
    # Phase 13.21 — sender_name to'ldirish
    names = await _resolve_author_names(db, [m.sender_id for m in items])
    serialized: list[MessagePublic] = []
    for m in items:
        pub = MessagePublic.model_validate(m)
        pub.sender_name = names.get(m.sender_id) if m.sender_id else None
        serialized.append(pub)
    return PaginatedMessages(items=serialized, has_more=has_more)


@router.post(
    "/chat/conversations/{conversation_id}/messages",
    response_model=MessagePublic,
    status_code=status.HTTP_201_CREATED,
    tags=["chat"],
)
async def send_message(
    conversation_id: int,
    payload: MessageCreate,
    db: DbSession,
    user: CurrentUser,
) -> MessagePublic:
    msg = await chat_service.send_message(
        db,
        conversation_id=conversation_id,
        sender_id=user.id,
        body=payload.body,
        attachment_url=payload.attachment_url,
        attachment_mime=payload.attachment_mime,
        attachment_size=payload.attachment_size,
        reply_to_id=payload.reply_to_id,
    )
    member_ids = await chat_service.get_member_ids(db, conversation_id)
    sender_name = user.full_name or f"user#{user.id}"
    await notifications_service.notify_new_chat_message(
        db,
        conversation_id=conversation_id,
        sender_id=user.id,
        sender_name=sender_name,
        body_preview=msg.body,
        recipient_ids=member_ids,
    )
    await db.commit()
    await db.refresh(msg)

    pub = MessagePublic.model_validate(msg)
    pub.sender_name = user.full_name
    serialized = pub.model_dump(mode="json")
    await ws_manager.publish_to_users(
        member_ids,
        {
            "type": "message.new",
            "conversation_id": conversation_id,
            "payload": serialized,
        },
    )
    return pub


@router.patch(
    "/chat/messages/{message_id}",
    response_model=MessagePublic,
    tags=["chat"],
)
async def edit_message(
    message_id: int,
    payload: MessageEdit,
    db: DbSession,
    user: CurrentUser,
) -> MessagePublic:
    msg = await chat_service.edit_message(db, message_id, user.id, payload.body)
    await db.commit()
    await db.refresh(msg)
    member_ids = await chat_service.get_member_ids(db, msg.conversation_id)
    pub = MessagePublic.model_validate(msg)
    pub.sender_name = user.full_name
    serialized = pub.model_dump(mode="json")
    await ws_manager.publish_to_users(
        member_ids,
        {
            "type": "message.edit",
            "conversation_id": msg.conversation_id,
            "payload": serialized,
        },
    )
    return pub


@router.delete(
    "/chat/messages/{message_id}",
    response_model=MessagePublic,
    tags=["chat"],
)
async def delete_message(
    message_id: int,
    db: DbSession,
    user: CurrentUser,
) -> MessagePublic:
    msg = await chat_service.delete_message(db, message_id, user.id)
    await db.commit()
    await db.refresh(msg)
    member_ids = await chat_service.get_member_ids(db, msg.conversation_id)
    await ws_manager.publish_to_users(
        member_ids,
        {
            "type": "message.delete",
            "conversation_id": msg.conversation_id,
            "payload": {"id": msg.id},
        },
    )
    pub = MessagePublic.model_validate(msg)
    if msg.sender_id is not None:
        names = await _resolve_author_names(db, [msg.sender_id])
        pub.sender_name = names.get(msg.sender_id)
    return pub


# ============================================================================
# Chat — WebSocket
# ============================================================================


@router.websocket("/chat/ws")
async def chat_websocket(websocket: WebSocket, token: str = Query(...)) -> None:
    """Realtime chat soketi.

    Auth: `?token=<access_jwt>` query parametr (browser WebSocket API header
    qo'sha olmaydi). Token noto'g'ri bo'lsa 1008.
    """
    try:
        payload = decode_token(token, expected_type="access")
        user_id = int(payload["sub"])
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # User'ni DB'da tekshirish (idempotent — bir oz qimmat lekin ws lifetime'da bir marta)
    async for db in get_db():
        u = await db.get(User, user_id)
        if u is None or not u.is_active or u.deleted_at is not None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        break

    await ws_manager.connect(user_id, websocket)
    try:
        while True:
            # Client typing/ping yuborishi mumkin
            msg = await websocket.receive_json()
            kind = msg.get("type")
            conv_id = msg.get("conversation_id")
            if kind == "typing" and isinstance(conv_id, int):
                async for db in get_db():
                    if not await chat_service.is_member(db, conv_id, user_id):
                        break
                    member_ids = await chat_service.get_member_ids(db, conv_id)
                    targets = [uid for uid in member_ids if uid != user_id]
                    if targets:
                        await ws_manager.publish_to_users(
                            targets,
                            {
                                "type": "typing",
                                "conversation_id": conv_id,
                                "payload": {"user_id": user_id},
                            },
                        )
                    break
            # Ignored types — keep connection alive
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(user_id, websocket)


# ============================================================================
# Forum — threads
# ============================================================================


@router.get(
    "/forum/courses/{course_id}/threads",
    response_model=PaginatedThreads,
    tags=["forum"],
)
async def list_forum_threads(
    course_id: int,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedThreads:
    items, total = await forum_service.list_threads(
        db, course_id, user.id, page=page, page_size=page_size
    )
    names = await _resolve_author_names(db, [t.author_id for t in items])
    serialized: list[ForumThreadPublic] = []
    for t in items:
        pub = ForumThreadPublic.model_validate(t)
        pub.author_name = names.get(t.author_id) if t.author_id else None
        serialized.append(pub)
    return PaginatedThreads(items=serialized, total=total)


@router.post(
    "/forum/threads",
    response_model=ForumThreadPublic,
    status_code=status.HTTP_201_CREATED,
    tags=["forum"],
)
async def create_forum_thread(
    payload: ForumThreadCreate,
    db: DbSession,
    user: CurrentUser,
) -> ForumThreadPublic:
    thread = await forum_service.create_thread(
        db,
        course_id=payload.course_id,
        author_id=user.id,
        title=payload.title,
        body=payload.body,
        lesson_id=payload.lesson_id,
        is_announcement=payload.is_announcement,
    )
    await db.commit()
    await db.refresh(thread)
    pub = ForumThreadPublic.model_validate(thread)
    pub.author_name = user.full_name
    return pub


@router.get(
    "/forum/threads/{thread_id}",
    response_model=ForumThreadPublic,
    tags=["forum"],
)
async def get_forum_thread(
    thread_id: int,
    db: DbSession,
    user: CurrentUser,
) -> ForumThreadPublic:
    thread = await forum_service.get_thread(db, thread_id, user.id)
    await db.commit()
    pub = ForumThreadPublic.model_validate(thread)
    if thread.author_id is not None:
        names = await _resolve_author_names(db, [thread.author_id])
        pub.author_name = names.get(thread.author_id)
    return pub


@router.patch(
    "/forum/threads/{thread_id}",
    response_model=ForumThreadPublic,
    tags=["forum"],
)
async def update_forum_thread(
    thread_id: int,
    payload: ForumThreadUpdate,
    db: DbSession,
    user: CurrentUser,
) -> ForumThreadPublic:
    thread = await forum_service.update_thread(
        db,
        thread_id,
        user.id,
        title=payload.title,
        body=payload.body,
        is_pinned=payload.is_pinned,
        is_locked=payload.is_locked,
    )
    await db.commit()
    await db.refresh(thread)
    pub = ForumThreadPublic.model_validate(thread)
    if thread.author_id is not None:
        names = await _resolve_author_names(db, [thread.author_id])
        pub.author_name = names.get(thread.author_id)
    return pub


@router.delete(
    "/forum/threads/{thread_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["forum"],
)
async def delete_forum_thread(
    thread_id: int,
    db: DbSession,
    user: CurrentUser,
) -> None:
    await forum_service.delete_thread(db, thread_id, user.id)
    await db.commit()


# ============================================================================
# Forum — posts
# ============================================================================


@router.get(
    "/forum/threads/{thread_id}/posts",
    response_model=PaginatedPosts,
    tags=["forum"],
)
async def list_forum_posts(
    thread_id: int,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> PaginatedPosts:
    items, total, liked_map = await forum_service.list_posts(
        db, thread_id, user.id, page=page, page_size=page_size
    )
    names = await _resolve_author_names(db, [p.author_id for p in items])
    serialized: list[ForumPostPublic] = []
    for p in items:
        pub = ForumPostPublic.model_validate(p)
        pub.liked_by_me = liked_map.get(p.id, False)
        pub.author_name = names.get(p.author_id) if p.author_id else None
        serialized.append(pub)
    return PaginatedPosts(items=serialized, total=total)


@router.post(
    "/forum/threads/{thread_id}/posts",
    response_model=ForumPostPublic,
    status_code=status.HTTP_201_CREATED,
    tags=["forum"],
)
async def create_forum_post(
    thread_id: int,
    payload: ForumPostCreate,
    db: DbSession,
    user: CurrentUser,
) -> ForumPostPublic:
    post = await forum_service.create_post(
        db,
        thread_id=thread_id,
        author_id=user.id,
        body=payload.body,
        parent_post_id=payload.parent_post_id,
    )
    # Mavzu muallifiga reply bildirishnomasi (o'zi javob bermasa)
    from app.modules.communications.models import ForumThread

    thread = await db.get(ForumThread, thread_id)
    if thread is not None and thread.author_id is not None:
        author_name = user.full_name or f"user#{user.id}"
        await notifications_service.notify_forum_reply(
            db,
            thread_id=thread_id,
            thread_title=thread.title,
            author_id=user.id,
            author_name=author_name,
            recipient_ids=[thread.author_id],
        )
    await db.commit()
    await db.refresh(post)
    pub = ForumPostPublic.model_validate(post)
    pub.author_name = user.full_name
    return pub


@router.patch(
    "/forum/posts/{post_id}",
    response_model=ForumPostPublic,
    tags=["forum"],
)
async def edit_forum_post(
    post_id: int,
    payload: ForumPostEdit,
    db: DbSession,
    user: CurrentUser,
) -> ForumPostPublic:
    post = await forum_service.edit_post(db, post_id, user.id, payload.body)
    await db.commit()
    await db.refresh(post)
    pub = ForumPostPublic.model_validate(post)
    pub.author_name = user.full_name
    return pub


@router.delete(
    "/forum/posts/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["forum"],
)
async def delete_forum_post(
    post_id: int,
    db: DbSession,
    user: CurrentUser,
) -> None:
    await forum_service.delete_post(db, post_id, user.id)
    await db.commit()


@router.post(
    "/forum/posts/{post_id}/like",
    response_model=ForumPostPublic,
    tags=["forum"],
)
async def toggle_forum_post_like(
    post_id: int,
    db: DbSession,
    user: CurrentUser,
) -> ForumPostPublic:
    post, liked = await forum_service.toggle_like(db, post_id, user.id)
    await db.commit()
    await db.refresh(post)
    pub = ForumPostPublic.model_validate(post)
    pub.liked_by_me = liked
    if post.author_id is not None:
        names = await _resolve_author_names(db, [post.author_id])
        pub.author_name = names.get(post.author_id)
    return pub


# ============================================================================
# Lesson comments (Phase 11c)
# ============================================================================


@router.get(
    "/lessons/{lesson_id}/comments",
    response_model=PaginatedComments,
    tags=["lesson-comments"],
)
async def list_lesson_comments(
    lesson_id: int,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> PaginatedComments:
    items, total, liked_map = await comments_service.list_comments(
        db, lesson_id, user.id, page=page, page_size=page_size
    )
    names = await _resolve_author_names(db, [c.author_id for c in items])
    serialized: list[LessonCommentPublic] = []
    for c in items:
        pub = LessonCommentPublic.model_validate(c)
        pub.liked_by_me = liked_map.get(c.id, False)
        pub.author_name = names.get(c.author_id) if c.author_id else None
        serialized.append(pub)
    return PaginatedComments(items=serialized, total=total)


@router.post(
    "/lessons/{lesson_id}/comments",
    response_model=LessonCommentPublic,
    status_code=status.HTTP_201_CREATED,
    tags=["lesson-comments"],
)
async def create_lesson_comment(
    lesson_id: int,
    payload: LessonCommentCreate,
    db: DbSession,
    user: CurrentUser,
) -> LessonCommentPublic:
    comment = await comments_service.create_comment(
        db,
        lesson_id=lesson_id,
        author_id=user.id,
        body=payload.body,
        parent_comment_id=payload.parent_comment_id,
    )
    await db.commit()
    await db.refresh(comment)
    pub = LessonCommentPublic.model_validate(comment)
    pub.author_name = user.full_name
    return pub


@router.patch(
    "/lessons/comments/{comment_id}",
    response_model=LessonCommentPublic,
    tags=["lesson-comments"],
)
async def edit_lesson_comment(
    comment_id: int,
    payload: LessonCommentEdit,
    db: DbSession,
    user: CurrentUser,
) -> LessonCommentPublic:
    comment = await comments_service.edit_comment(
        db, comment_id, user.id, payload.body
    )
    await db.commit()
    await db.refresh(comment)
    pub = LessonCommentPublic.model_validate(comment)
    pub.author_name = user.full_name
    return pub


@router.delete(
    "/lessons/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["lesson-comments"],
)
async def delete_lesson_comment(
    comment_id: int,
    db: DbSession,
    user: CurrentUser,
) -> None:
    await comments_service.delete_comment(db, comment_id, user.id)
    await db.commit()


@router.post(
    "/lessons/comments/{comment_id}/like",
    response_model=LessonCommentPublic,
    tags=["lesson-comments"],
)
async def toggle_lesson_comment_like(
    comment_id: int,
    db: DbSession,
    user: CurrentUser,
) -> LessonCommentPublic:
    comment, liked = await comments_service.toggle_like(db, comment_id, user.id)
    await db.commit()
    await db.refresh(comment)
    pub = LessonCommentPublic.model_validate(comment)
    pub.liked_by_me = liked
    if comment.author_id is not None:
        names = await _resolve_author_names(db, [comment.author_id])
        pub.author_name = names.get(comment.author_id)
    return pub

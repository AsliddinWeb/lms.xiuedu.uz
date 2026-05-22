"""Forum service — Phase 11b.

Course-scoped muhokama. Threads + posts (nested via parent_post_id) + likes.
Pin/lock/announcement — pedagog/admin huquqida.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.modules.communications.models import (
    ForumPost,
    ForumPostLike,
    ForumThread,
)
from app.modules.courses.models import Course, Enrollment


def _now() -> datetime:
    return datetime.now(UTC)


# ============================================================================
# Authorization helpers
# ============================================================================


async def _is_course_member(
    db: AsyncSession, course_id: int, user_id: int
) -> tuple[bool, bool]:
    """`(is_member, is_instructor_or_admin)` qaytaradi."""
    course = await db.get(Course, course_id)
    if course is None:
        raise NotFoundError("Kurs topilmadi")
    if course.primary_author_id == user_id:
        return True, True

    enrolled = (
        await db.execute(
            select(Enrollment.id).where(
                Enrollment.course_id == course_id,
                Enrollment.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    return enrolled is not None, False


async def _assert_course_access(
    db: AsyncSession, course_id: int, user_id: int
) -> tuple[bool, bool]:
    is_member, is_instructor = await _is_course_member(db, course_id, user_id)
    if not is_member:
        raise ForbiddenError("Bu kurs forumiga kirish ruxsati yo'q")
    return is_member, is_instructor


# ============================================================================
# Threads
# ============================================================================


async def list_threads(
    db: AsyncSession,
    course_id: int,
    user_id: int,
    *,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ForumThread], int]:
    await _assert_course_access(db, course_id, user_id)
    base = select(ForumThread).where(
        ForumThread.course_id == course_id,
        ForumThread.deleted_at.is_(None),
    )
    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()
    stmt = (
        base.order_by(
            ForumThread.is_pinned.desc(),
            ForumThread.last_reply_at.desc().nullslast(),
            ForumThread.created_at.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await db.execute(stmt)).scalars().all()
    return list(items), int(total)


async def get_thread(
    db: AsyncSession, thread_id: int, user_id: int, *, bump_view: bool = True
) -> ForumThread:
    thread = await db.get(ForumThread, thread_id)
    if thread is None or thread.deleted_at is not None:
        raise NotFoundError("Mavzu topilmadi")
    await _assert_course_access(db, thread.course_id, user_id)
    if bump_view:
        thread.view_count += 1
        await db.flush()
    return thread


async def create_thread(
    db: AsyncSession,
    *,
    course_id: int,
    author_id: int,
    title: str,
    body: str | None,
    lesson_id: int | None = None,
    is_announcement: bool = False,
) -> ForumThread:
    _, is_instructor = await _assert_course_access(db, course_id, author_id)
    if is_announcement and not is_instructor:
        raise ForbiddenError("Faqat o'qituvchi e'lon yaratadi")

    thread = ForumThread(
        course_id=course_id,
        lesson_id=lesson_id,
        author_id=author_id,
        title=title,
        body=body,
        is_announcement=is_announcement,
        last_reply_at=_now(),
    )
    db.add(thread)
    await db.flush()

    # Phase 11e — gamification (e'lon uchun ball yo'q)
    if not is_announcement:
        from app.modules.gamification import service as gamif_service

        try:
            await gamif_service.award_event(
                db,
                user_id=author_id,
                event_type="forum.thread.created",
                context={"thread_id": thread.id, "course_id": course_id},
                dedupe_key=f"forum.thread.created:{thread.id}",
            )
        except Exception:  # noqa: BLE001
            pass

    return thread


async def update_thread(
    db: AsyncSession,
    thread_id: int,
    user_id: int,
    *,
    title: str | None = None,
    body: str | None = None,
    is_pinned: bool | None = None,
    is_locked: bool | None = None,
) -> ForumThread:
    thread = await get_thread(db, thread_id, user_id, bump_view=False)
    _, is_instructor = await _is_course_member(db, thread.course_id, user_id)

    is_author = thread.author_id == user_id

    if title is not None or body is not None:
        if not is_author and not is_instructor:
            raise ForbiddenError("Faqat muallif yoki o'qituvchi tahrirlay oladi")
        if title is not None:
            thread.title = title
        if body is not None:
            thread.body = body

    if is_pinned is not None or is_locked is not None:
        if not is_instructor:
            raise ForbiddenError("Faqat o'qituvchi pin/lock qila oladi")
        if is_pinned is not None:
            thread.is_pinned = is_pinned
        if is_locked is not None:
            thread.is_locked = is_locked

    await db.flush()
    return thread


async def delete_thread(
    db: AsyncSession, thread_id: int, user_id: int
) -> ForumThread:
    thread = await get_thread(db, thread_id, user_id, bump_view=False)
    _, is_instructor = await _is_course_member(db, thread.course_id, user_id)
    if thread.author_id != user_id and not is_instructor:
        raise ForbiddenError("O'chirish ruxsati yo'q")
    thread.deleted_at = _now()
    await db.flush()
    return thread


# ============================================================================
# Posts
# ============================================================================


async def list_posts(
    db: AsyncSession,
    thread_id: int,
    user_id: int,
    *,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[ForumPost], int, dict[int, bool]]:
    """Mavzu ichidagi javoblar + `liked_by_me` map."""
    thread = await get_thread(db, thread_id, user_id, bump_view=False)
    base = select(ForumPost).where(
        ForumPost.thread_id == thread.id,
        ForumPost.deleted_at.is_(None),
    )
    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()
    stmt = (
        base.order_by(ForumPost.created_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())

    if items:
        post_ids = [p.id for p in items]
        liked_rows = (
            await db.execute(
                select(ForumPostLike.post_id).where(
                    ForumPostLike.post_id.in_(post_ids),
                    ForumPostLike.user_id == user_id,
                )
            )
        ).scalars().all()
        liked_map = {pid: (pid in set(liked_rows)) for pid in post_ids}
    else:
        liked_map = {}
    return items, int(total), liked_map


async def create_post(
    db: AsyncSession,
    *,
    thread_id: int,
    author_id: int,
    body: str,
    parent_post_id: int | None = None,
) -> ForumPost:
    thread = await get_thread(db, thread_id, author_id, bump_view=False)
    if thread.is_locked:
        raise ForbiddenError("Mavzu yopilgan")
    if thread.is_announcement:
        _, is_instructor = await _is_course_member(db, thread.course_id, author_id)
        if not is_instructor:
            raise ForbiddenError("E'longa javob berish mumkin emas")

    if parent_post_id is not None:
        parent = await db.get(ForumPost, parent_post_id)
        if parent is None or parent.thread_id != thread.id:
            raise NotFoundError("Parent post topilmadi")

    post = ForumPost(
        thread_id=thread.id,
        author_id=author_id,
        body=body,
        parent_post_id=parent_post_id,
    )
    db.add(post)
    await db.flush()

    thread.post_count += 1
    thread.last_reply_at = post.created_at
    await db.flush()

    # Phase 11e — gamification
    from app.modules.gamification import service as gamif_service

    try:
        await gamif_service.award_event(
            db,
            user_id=author_id,
            event_type="forum.post.created",
            context={"post_id": post.id, "thread_id": thread.id},
            dedupe_key=f"forum.post.created:{post.id}",
        )
    except Exception:  # noqa: BLE001
        pass

    return post


async def edit_post(
    db: AsyncSession, post_id: int, user_id: int, new_body: str
) -> ForumPost:
    post = await db.get(ForumPost, post_id)
    if post is None or post.deleted_at is not None:
        raise NotFoundError("Post topilmadi")
    if post.author_id != user_id:
        raise ForbiddenError("Faqat muallif tahrirlay oladi")
    post.body = new_body
    post.edited_at = _now()
    await db.flush()
    return post


async def delete_post(
    db: AsyncSession, post_id: int, user_id: int
) -> ForumPost:
    post = await db.get(ForumPost, post_id)
    if post is None or post.deleted_at is not None:
        raise NotFoundError("Post topilmadi")
    thread = await db.get(ForumThread, post.thread_id)
    if thread is None:
        raise NotFoundError("Mavzu topilmadi")
    _, is_instructor = await _is_course_member(db, thread.course_id, user_id)
    if post.author_id != user_id and not is_instructor:
        raise ForbiddenError("O'chirish ruxsati yo'q")
    post.deleted_at = _now()
    thread.post_count = max(0, thread.post_count - 1)
    await db.flush()
    return post


# ============================================================================
# Likes
# ============================================================================


async def toggle_like(
    db: AsyncSession, post_id: int, user_id: int
) -> tuple[ForumPost, bool]:
    """`(post, is_liked)` qaytaradi."""
    post = await db.get(ForumPost, post_id)
    if post is None or post.deleted_at is not None:
        raise NotFoundError("Post topilmadi")
    # Course membership tekshiruv
    thread = await db.get(ForumThread, post.thread_id)
    if thread is None:
        raise NotFoundError("Mavzu topilmadi")
    await _assert_course_access(db, thread.course_id, user_id)

    existing = await db.get(ForumPostLike, (post_id, user_id))
    if existing is None:
        db.add(ForumPostLike(post_id=post_id, user_id=user_id))
        post.like_count += 1
        liked = True
    else:
        await db.delete(existing)
        post.like_count = max(0, post.like_count - 1)
        liked = False
    await db.flush()

    # Phase 11e — muallifga ball (faqat birinchi like'da; dedupe key bilan)
    # O'zining post'iga like bermasa
    if liked and post.author_id is not None and post.author_id != user_id:
        from app.modules.gamification import service as gamif_service

        try:
            await gamif_service.award_event(
                db,
                user_id=post.author_id,
                event_type="forum.post.liked",
                context={"post_id": post.id, "liker_id": user_id},
                dedupe_key=f"forum.post.liked:{post.id}:{user_id}",
            )
        except Exception:  # noqa: BLE001
            pass

    return post, liked

"""Lesson comments service — Phase 11c.

Dars izohlari (lesson comments). Forum'dan farqli — yengilroq, lesson darajasida,
faqat 1 darajali reply (parent_comment_id self-FK).

Ruxsat:
    - O'qish: lesson tegishli kursga enroll bo'lgan yoki o'qituvchi
    - Yozish: shu ruxsatga ega user (talaba/o'qituvchi)
    - Tahrir/o'chirish: muallif yoki kurs muallifi (o'qituvchi)
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.modules.communications.models import LessonComment, LessonCommentLike
from app.modules.courses.models import Course, Enrollment, Lesson, Module


def _now() -> datetime:
    return datetime.now(UTC)


# ============================================================================
# Authorization
# ============================================================================


async def _resolve_course(db: AsyncSession, lesson_id: int) -> Course:
    """Lesson'dan uning kursini topib qaytaradi."""
    stmt = (
        select(Course)
        .join(Module, Module.course_id == Course.id)
        .join(Lesson, Lesson.module_id == Module.id)
        .where(Lesson.id == lesson_id)
    )
    course = (await db.execute(stmt)).scalar_one_or_none()
    if course is None:
        raise NotFoundError("Dars topilmadi")
    return course


async def _assert_lesson_access(
    db: AsyncSession, lesson_id: int, user_id: int
) -> tuple[Course, bool]:
    """`(course, is_instructor)` qaytaradi yoki 403."""
    course = await _resolve_course(db, lesson_id)
    if course.primary_author_id == user_id:
        return course, True

    enrolled = (
        await db.execute(
            select(Enrollment.id).where(
                Enrollment.course_id == course.id,
                Enrollment.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if enrolled is None:
        raise ForbiddenError("Bu darsga kirish ruxsati yo'q")
    return course, False


# ============================================================================
# Listing + create
# ============================================================================


async def list_comments(
    db: AsyncSession,
    lesson_id: int,
    user_id: int,
    *,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[LessonComment], int, dict[int, bool]]:
    """Izohlar ro'yxati + `liked_by_me` map. Eski → yangi tartibda."""
    await _assert_lesson_access(db, lesson_id, user_id)

    base = select(LessonComment).where(
        LessonComment.lesson_id == lesson_id,
        LessonComment.deleted_at.is_(None),
    )
    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()
    stmt = (
        base.order_by(LessonComment.created_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())

    if items:
        comment_ids = [c.id for c in items]
        liked_rows = (
            await db.execute(
                select(LessonCommentLike.comment_id).where(
                    LessonCommentLike.comment_id.in_(comment_ids),
                    LessonCommentLike.user_id == user_id,
                )
            )
        ).scalars().all()
        liked_set = set(liked_rows)
        liked_map = {cid: (cid in liked_set) for cid in comment_ids}
    else:
        liked_map = {}
    return items, int(total), liked_map


async def create_comment(
    db: AsyncSession,
    *,
    lesson_id: int,
    author_id: int,
    body: str,
    parent_comment_id: int | None = None,
) -> LessonComment:
    await _assert_lesson_access(db, lesson_id, author_id)

    if parent_comment_id is not None:
        parent = await db.get(LessonComment, parent_comment_id)
        if parent is None or parent.lesson_id != lesson_id:
            raise NotFoundError("Javob beriladigan izoh topilmadi")
        # Faqat 1 daraja — parent o'zi reply bo'lsa, uning parent'iga ko'tarib qo'yamiz
        if parent.parent_comment_id is not None:
            parent_comment_id = parent.parent_comment_id

    comment = LessonComment(
        lesson_id=lesson_id,
        author_id=author_id,
        body=body,
        parent_comment_id=parent_comment_id,
    )
    db.add(comment)
    await db.flush()

    # Phase 11e — gamification
    from app.modules.gamification import service as gamif_service

    try:
        await gamif_service.award_event(
            db,
            user_id=author_id,
            event_type="comment.created",
            context={"comment_id": comment.id, "lesson_id": lesson_id},
            dedupe_key=f"comment.created:{comment.id}",
        )
    except Exception:  # noqa: BLE001
        pass

    return comment


# ============================================================================
# Edit / delete
# ============================================================================


async def edit_comment(
    db: AsyncSession, comment_id: int, user_id: int, new_body: str
) -> LessonComment:
    comment = await db.get(LessonComment, comment_id)
    if comment is None or comment.deleted_at is not None:
        raise NotFoundError("Izoh topilmadi")
    if comment.author_id != user_id:
        raise ForbiddenError("Faqat muallif tahrirlay oladi")
    comment.body = new_body
    comment.edited_at = _now()
    await db.flush()
    return comment


async def delete_comment(
    db: AsyncSession, comment_id: int, user_id: int
) -> LessonComment:
    """Soft delete — muallif yoki kurs muallifi (o'qituvchi)."""
    comment = await db.get(LessonComment, comment_id)
    if comment is None or comment.deleted_at is not None:
        raise NotFoundError("Izoh topilmadi")

    course = await _resolve_course(db, comment.lesson_id)
    is_instructor = course.primary_author_id == user_id

    if comment.author_id != user_id and not is_instructor:
        raise ForbiddenError("O'chirish ruxsati yo'q")

    comment.deleted_at = _now()
    await db.flush()
    return comment


# ============================================================================
# Likes
# ============================================================================


async def toggle_like(
    db: AsyncSession, comment_id: int, user_id: int
) -> tuple[LessonComment, bool]:
    comment = await db.get(LessonComment, comment_id)
    if comment is None or comment.deleted_at is not None:
        raise NotFoundError("Izoh topilmadi")
    await _assert_lesson_access(db, comment.lesson_id, user_id)

    existing = await db.get(LessonCommentLike, (comment_id, user_id))
    if existing is None:
        db.add(LessonCommentLike(comment_id=comment_id, user_id=user_id))
        comment.like_count += 1
        liked = True
    else:
        await db.delete(existing)
        comment.like_count = max(0, comment.like_count - 1)
        liked = False
    await db.flush()
    return comment, liked

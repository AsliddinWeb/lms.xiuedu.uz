"""Content CRUD service (Phase 3a).

Workflow:
    draft → review → published → archived
Foydalanuvchi `content.publish` permissioniga ega bo'lsa to'g'ridan-to'g'ri publish
qila oladi (lekin minimal MVP'da review state'i optional).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.academic.models import Subject
from app.modules.content.models import ContentItem
from app.modules.content.schemas import (
    ContentCreateRequest,
    ContentUpdateRequest,
)


def _now() -> datetime:
    return datetime.now(UTC)


VALID_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"review", "published", "archived"},
    "review": {"draft", "published", "archived"},
    "published": {"archived"},
    "archived": {"draft"},  # qayta tahrirlash uchun
}


async def list_content(
    db: AsyncSession,
    *,
    type_: str | None,
    status_: str | None,
    subject_id: int | None,
    author_id: int | None,
    language: str | None,
    q: str | None,
    page: int,
    page_size: int,
) -> tuple[list[ContentItem], int]:
    stmt = select(ContentItem).where(ContentItem.deleted_at.is_(None))
    if type_ is not None:
        stmt = stmt.where(ContentItem.type == type_)
    if status_ is not None:
        stmt = stmt.where(ContentItem.status == status_)
    if subject_id is not None:
        stmt = stmt.where(ContentItem.subject_id == subject_id)
    if author_id is not None:
        stmt = stmt.where(ContentItem.author_id == author_id)
    if language is not None:
        stmt = stmt.where(ContentItem.language == language)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(ContentItem.title).like(like),
                func.lower(ContentItem.description).like(like),
            )
        )

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = (
        stmt.order_by(desc(ContentItem.id))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, int(total)


async def get_content(db: AsyncSession, content_id: int) -> ContentItem:
    stmt = select(ContentItem).where(
        ContentItem.id == content_id, ContentItem.deleted_at.is_(None)
    )
    item = (await db.execute(stmt)).scalar_one_or_none()
    if item is None:
        raise NotFoundError("Kontent topilmadi")
    return item


async def create_content(
    db: AsyncSession, data: ContentCreateRequest, *, author_id: int
) -> ContentItem:
    if data.subject_id is not None:
        if (await db.get(Subject, data.subject_id)) is None:
            raise NotFoundError(f"Fan id={data.subject_id} topilmadi")

    payload = data.model_dump()
    item = ContentItem(
        author_id=author_id,
        status="draft",
        version=1,
        **payload,
    )
    db.add(item)
    await db.flush()
    return item


async def update_content(
    db: AsyncSession, content_id: int, data: ContentUpdateRequest
) -> ContentItem:
    item = await get_content(db, content_id)
    if item.status == "published":
        raise ConflictError(
            "Published kontentni tahrirlab bo'lmaydi — yangi versiya yarating yoki archive qiling"
        )
    if data.subject_id is not None:
        if (await db.get(Subject, data.subject_id)) is None:
            raise NotFoundError(f"Fan id={data.subject_id} topilmadi")

    update = data.model_dump(exclude_unset=True)
    for k, v in update.items():
        setattr(item, k, v)
    await db.flush()
    await db.refresh(item)
    return item


async def delete_content(db: AsyncSession, content_id: int) -> None:
    """Soft-delete: deleted_at sanasi qo'yiladi."""
    item = await get_content(db, content_id)
    item.deleted_at = _now()
    await db.flush()


async def transition_status(
    db: AsyncSession, content_id: int, *, new_status: str
) -> ContentItem:
    item = await get_content(db, content_id)
    allowed = VALID_TRANSITIONS.get(item.status, set())
    if new_status not in allowed:
        allowed_text = ", ".join(sorted(allowed)) if allowed else "(hech narsa)"
        raise ValidationError(
            f"'{item.status}' -> '{new_status}' o'tish ruxsat etilmagan. "
            f"Ruxsat etilgan: {allowed_text}"
        )
    item.status = new_status
    if new_status == "published":
        item.published_at = _now()
    await db.flush()
    await db.refresh(item)
    return item


async def attach_uploaded_file(
    db: AsyncSession,
    content_id: int,
    *,
    file_url: str,
    mime_type: str,
    file_size: int,
) -> ContentItem:
    item = await get_content(db, content_id)
    if item.status == "published":
        raise ConflictError(
            "Published kontentga fayl biriktirib bo'lmaydi — avval archive qiling"
        )
    item.file_url = file_url
    item.mime_type = mime_type
    item.file_size = file_size
    await db.flush()
    await db.refresh(item)
    return item

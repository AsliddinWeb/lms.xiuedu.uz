"""Content endpointlari (Phase 3a).

7 ta endpoint:
    GET    /content              — ro'yxat (filter + pagination)
    POST   /content              — yangi kontent (draft)
    GET    /content/{id}         — bitta kontent
    PATCH  /content/{id}         — tahrirlash (faqat draft/review/archived)
    DELETE /content/{id}         — soft-delete
    POST   /content/{id}/publish — publish/transition
    POST   /content/{id}/upload  — fayl yuklash (multipart, max 100 MB)
"""

from __future__ import annotations

import secrets
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel

from app.core.exceptions import ForbiddenError
from app.core.storage import delete_object, object_key_from_url, upload_object
from app.modules.auth.dependencies import (
    CurrentUser,
    DbSession,
    RedisClient,
    require_permission,
)
from app.modules.content import service
from app.modules.content.models import ContentItem
from app.modules.content.schemas import (
    ContentCreateRequest,
    ContentPublic,
    ContentUpdateRequest,
    ContentUploadResponse,
    PaginatedContent,
)
from app.modules.rbac.service import RBACService, has_permission
from app.modules.users.models import User

router = APIRouter(prefix="/content", tags=["content"])


async def _require_content_author(
    db: DbSession,
    redis: RedisClient,
    actor: User,
    item: ContentItem,
) -> None:
    """Faqat kontent muallifi yoki platform.* permissioniga ega user
    tahrir/o'chirish/transition qila oladi."""
    if item.author_id == actor.id:
        return
    rbac = RBACService(db, redis)
    perms = await rbac.get_user_permissions(actor.id)
    if has_permission(perms, "platform.*"):
        return
    raise ForbiddenError("Faqat kontent muallifi yoki platform admin tahrir qila oladi")


# 100 MB
CONTENT_MAX_BYTES = 100 * 1024 * 1024
ALLOWED_CONTENT_MIME = {
    # video
    "video/mp4",
    "video/webm",
    "video/quicktime",
    # documents
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    # archives
    "application/zip",
    "application/x-zip-compressed",
    # images (kontentdagi rasm — slayd bo'lishi mumkin)
    "image/jpeg",
    "image/png",
    "image/webp",
    # audio
    "audio/mpeg",
    "audio/wav",
    "audio/ogg",
}


class ContentTransitionRequest(BaseModel):
    """`/content/{id}/publish` body — yangi statusni ko'rsatish."""

    status: Literal["draft", "review", "published", "archived"]


@router.get("", response_model=PaginatedContent, summary="Kontent ro'yxati")
async def list_content(
    db: DbSession,
    _u: User = Depends(require_permission("content.read")),
    type: str | None = Query(None, description="text | video | pdf | file | link"),
    status_: str | None = Query(
        None, alias="status", description="draft | review | published | archived"
    ),
    subject_id: int | None = Query(None),
    author_id: int | None = Query(None),
    language: str | None = Query(None),
    q: str | None = Query(None, description="Title/description bo'yicha qidirish"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedContent:
    items, total = await service.list_content(
        db,
        type_=type,
        status_=status_,
        subject_id=subject_id,
        author_id=author_id,
        language=language,
        q=q,
        page=page,
        page_size=page_size,
    )
    return PaginatedContent(
        items=[ContentPublic.model_validate(i) for i in items], total=total
    )


@router.post(
    "",
    response_model=ContentPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi kontent yaratish (draft)",
)
async def create_content(
    data: ContentCreateRequest,
    db: DbSession,
    actor: CurrentUser,
    _u: User = Depends(require_permission("content.create")),
) -> ContentPublic:
    item = await service.create_content(db, data, author_id=actor.id)
    await db.commit()
    return ContentPublic.model_validate(item)


@router.get("/{content_id}", response_model=ContentPublic, summary="Bitta kontent")
async def get_content(
    content_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("content.read")),
) -> ContentPublic:
    return ContentPublic.model_validate(await service.get_content(db, content_id))


@router.patch("/{content_id}", response_model=ContentPublic, summary="Kontent tahrirlash")
async def update_content(
    content_id: int,
    data: ContentUpdateRequest,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("content.create")),
) -> ContentPublic:
    existing = await service.get_content(db, content_id)
    await _require_content_author(db, redis, actor, existing)
    item = await service.update_content(db, content_id, data)
    await db.commit()
    return ContentPublic.model_validate(item)


@router.delete(
    "/{content_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Kontentni soft-delete qilish",
)
async def delete_content(
    content_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("content.create")),
) -> Response:
    existing = await service.get_content(db, content_id)
    await _require_content_author(db, redis, actor, existing)
    await service.delete_content(db, content_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{content_id}/publish",
    response_model=ContentPublic,
    summary="Kontent statusini o'zgartirish (publish/review/archive)",
)
async def transition_content(
    content_id: int,
    data: ContentTransitionRequest,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("content.publish")),
) -> ContentPublic:
    existing = await service.get_content(db, content_id)
    await _require_content_author(db, redis, actor, existing)
    item = await service.transition_status(db, content_id, new_status=data.status)
    await db.commit()
    return ContentPublic.model_validate(item)


@router.post(
    "/{content_id}/upload",
    response_model=ContentUploadResponse,
    summary="Fayl yuklash (max 100 MB)",
)
async def upload_content_file(
    content_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("content.create")),
    file: UploadFile = File(..., description="Yuklanadigan fayl (max 100 MB)"),
) -> ContentUploadResponse:
    # Mavjudligini va statusini tekshirish + author scope
    item = await service.get_content(db, content_id)
    await _require_content_author(db, redis, actor, item)

    contents = await file.read()
    if len(contents) > CONTENT_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Fayl hajmi 100 MB dan oshmasligi kerak (joriy: {len(contents)} bytes)"
            ),
        )

    ctype = (file.content_type or "application/octet-stream").lower()
    if ctype not in ALLOWED_CONTENT_MIME:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Fayl formati qo'llab-quvvatlanmaydi: {ctype}",
        )

    filename = file.filename or "content"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"

    # Eski fayl bo'lsa o'chirish (qayta yuklashda bo'sh joy ushlanmasin)
    old_key = object_key_from_url(item.file_url)
    if old_key:
        delete_object(old_key)

    object_name = f"content/{content_id}/{secrets.token_hex(8)}.{ext}"
    public_url = upload_object(
        object_name=object_name,
        data=contents,
        content_type=ctype,
    )
    item = await service.attach_uploaded_file(
        db,
        content_id,
        file_url=public_url,
        mime_type=ctype,
        file_size=len(contents),
    )
    await db.commit()
    return ContentUploadResponse(
        id=item.id, file_url=public_url, mime_type=ctype, file_size=len(contents)
    )

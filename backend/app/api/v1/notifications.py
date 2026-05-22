"""Notification endpoints — Phase 7d.

7 ta endpoint:
    GET    /notifications                  ro'yxat (filter: unread_only)
    GET    /notifications/unread-count     unread soni (topbar bell uchun)
    POST   /notifications/{id}/read        bittasini o'qildi
    POST   /notifications/read-all         hammasini o'qildi
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.core.exceptions import NotFoundError
from app.modules.auth.dependencies import CurrentUser, DbSession
from app.modules.notifications import service as notifications_service
from app.modules.notifications.schemas import (
    MarkAllReadResponse,
    NotificationPublic,
    PaginatedNotifications,
    UnreadCountResponse,
)

router = APIRouter()


@router.get("/notifications", response_model=PaginatedNotifications)
async def list_notifications(
    db: DbSession,
    user: CurrentUser,
    unread_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedNotifications:
    items, total = await notifications_service.list_for_user(
        db,
        user.id,
        unread_only=unread_only,
        page=page,
        page_size=page_size,
    )
    unread = await notifications_service.count_unread(db, user.id)
    return PaginatedNotifications(
        items=[NotificationPublic.model_validate(n) for n in items],
        total=total,
        unread_count=unread,
    )


@router.get("/notifications/unread-count", response_model=UnreadCountResponse)
async def unread_count(
    db: DbSession,
    user: CurrentUser,
) -> UnreadCountResponse:
    count = await notifications_service.count_unread(db, user.id)
    return UnreadCountResponse(count=count)


@router.post("/notifications/{notification_id}/read", response_model=NotificationPublic)
async def mark_one_read(
    notification_id: int,
    db: DbSession,
    user: CurrentUser,
) -> NotificationPublic:
    n = await notifications_service.mark_read(db, notification_id, user.id)
    if n is None:
        raise NotFoundError("Bildirishnoma topilmadi")
    await db.commit()
    return NotificationPublic.model_validate(n)


@router.post("/notifications/read-all", response_model=MarkAllReadResponse)
async def mark_all_read(
    db: DbSession,
    user: CurrentUser,
) -> MarkAllReadResponse:
    marked = await notifications_service.mark_all_read(db, user.id)
    await db.commit()
    return MarkAllReadResponse(marked=marked)

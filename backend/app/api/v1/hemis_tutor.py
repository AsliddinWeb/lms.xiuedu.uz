"""Phase 10g — Pedagog uchun HEMIS tutor data proxy.

LMS pedagog (teacher role) o'zining HEMIS guruh ma'lumotlarini bizning API
orqali ko'rishi mumkin. Token Redis cache'dan olinadi (Phase 10g login da
saqlangan). Cache yo'q bo'lsa 401 — pedagog HEMIS bilan qayta login qilishi
kerak.

Endpoint'lar:
    GET /tutor/hemis/profile        — pedagog profili
    GET /tutor/hemis/groups         — biriktirilgan guruhlar
    GET /tutor/hemis/groups/{id}/students
    GET /tutor/hemis/groups/{id}/gpa
    GET /tutor/hemis/groups/{id}/attendance?subject_id=
    GET /tutor/hemis/groups/{id}/debtors
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.integrations.hemis.client import (
    HemisAuthError,
    HemisClient,
    HemisError,
)
from app.integrations.hemis.token_cache import HemisTokenCache
from app.modules.auth.dependencies import (
    CurrentUser,
    RedisClient,
    require_permission,
)
from app.modules.users.models import User

router = APIRouter(prefix="/tutor/hemis", tags=["hemis_tutor"])


async def _get_tutor_token(
    redis: Any, user: User
) -> str:
    """Cache'dan tutor token olish. Bo'lmasa 401 — qayta login kerak.

    HEMIS tutor login (`/auth/login/hemis-tutor`) muvaffaqiyatli bo'lganda
    `HemisTokenCache.set_tutor(user.id, ...)` chaqiriladi (Phase 10g.1).
    Cache TTL 600s (10 min). Expire bo'lsa pedagog qayta login qilishi shart.
    """
    cache = HemisTokenCache(redis)
    pair = await cache.get_tutor(user.id)
    if not pair or not pair.get("token"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "HEMIS tutor sessiyasi muddati o'tgan. Qaytadan HEMIS pedagog "
                "kirishini amalga oshiring."
            ),
        )
    return pair["token"]


@router.get("/profile", summary="HEMIS pedagog profili")
async def get_tutor_profile(
    redis: RedisClient,
    user: CurrentUser,
    _u: User = Depends(require_permission("course.create")),
) -> dict[str, Any]:
    token = await _get_tutor_token(redis, user)
    try:
        async with HemisClient() as client:
            return await client.tutor_profile(token)
    except HemisAuthError:
        raise HTTPException(401, "HEMIS token yaroqsiz")
    except HemisError as exc:
        raise HTTPException(502, f"HEMIS unreachable: {exc}")


@router.get("/groups", summary="Pedagogga biriktirilgan guruhlar")
async def list_tutor_groups(
    redis: RedisClient,
    user: CurrentUser,
    _u: User = Depends(require_permission("course.create")),
) -> list[dict[str, Any]]:
    token = await _get_tutor_token(redis, user)
    try:
        async with HemisClient() as client:
            return await client.tutor_groups(token)
    except HemisAuthError:
        raise HTTPException(401, "HEMIS token yaroqsiz")
    except HemisError as exc:
        raise HTTPException(502, f"HEMIS unreachable: {exc}")


@router.get("/groups/{group_id}/students", summary="Guruh talabalari (HEMIS)")
async def list_tutor_group_students(
    group_id: int,
    redis: RedisClient,
    user: CurrentUser,
    _u: User = Depends(require_permission("course.create")),
) -> list[dict[str, Any]]:
    token = await _get_tutor_token(redis, user)
    try:
        async with HemisClient() as client:
            return await client.tutor_group_students(token, group_id)
    except HemisAuthError:
        raise HTTPException(401, "HEMIS token yaroqsiz")
    except HemisError as exc:
        raise HTTPException(502, f"HEMIS unreachable: {exc}")


@router.get("/groups/{group_id}/gpa", summary="Guruh GPA reytingi (HEMIS)")
async def get_tutor_group_gpa(
    group_id: int,
    redis: RedisClient,
    user: CurrentUser,
    _u: User = Depends(require_permission("course.create")),
) -> list[dict[str, Any]]:
    token = await _get_tutor_token(redis, user)
    try:
        async with HemisClient() as client:
            return await client.tutor_grade_gpa(token, group_id)
    except HemisAuthError:
        raise HTTPException(401, "HEMIS token yaroqsiz")
    except HemisError as exc:
        raise HTTPException(502, f"HEMIS unreachable: {exc}")


@router.get(
    "/groups/{group_id}/attendance",
    summary="Fan bo'yicha guruh davomati (HEMIS)",
)
async def get_tutor_group_attendance(
    group_id: int,
    redis: RedisClient,
    user: CurrentUser,
    subject_id: int | None = Query(default=None),
    _u: User = Depends(require_permission("course.create")),
) -> list[dict[str, Any]]:
    token = await _get_tutor_token(redis, user)
    try:
        async with HemisClient() as client:
            return await client.tutor_attendance_by_subject(
                token, group_id, subject_id
            )
    except HemisAuthError:
        raise HTTPException(401, "HEMIS token yaroqsiz")
    except HemisError as exc:
        raise HTTPException(502, f"HEMIS unreachable: {exc}")


@router.get("/groups/{group_id}/debtors", summary="Qarzdor talabalar (HEMIS)")
async def get_tutor_group_debtors(
    group_id: int,
    redis: RedisClient,
    user: CurrentUser,
    _u: User = Depends(require_permission("course.create")),
) -> list[dict[str, Any]]:
    token = await _get_tutor_token(redis, user)
    try:
        async with HemisClient() as client:
            return await client.tutor_grade_debtors(token, group_id)
    except HemisAuthError:
        raise HTTPException(401, "HEMIS token yaroqsiz")
    except HemisError as exc:
        raise HTTPException(502, f"HEMIS unreachable: {exc}")

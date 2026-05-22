"""FastAPI auth/RBAC dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError
from app.core.redis import get_redis
from app.core.security import decode_token
from app.modules.auth.exceptions import InvalidTokenError
from app.modules.auth.schemas import AuthContext
from app.modules.rbac.service import RBACService, has_permission
from app.modules.users.models import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_context(
    request: Request,
    user_agent: Annotated[str | None, Header(alias="User-Agent")] = None,
) -> AuthContext:
    """IP + UA ni request'dan olib AuthContext qaytaradi."""
    # X-Forwarded-For (proxy ortida) yoki client.host
    ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "0.0.0.0")
    )
    return AuthContext(ip_address=ip, user_agent=user_agent)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise InvalidTokenError("Authorization header talab qilinadi")

    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except ValueError as exc:
        raise InvalidTokenError(str(exc)) from exc

    user_id = int(payload["sub"])
    user = await db.get(User, user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise InvalidTokenError("Foydalanuvchi topilmadi yoki o'chirilgan")
    return user


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials, db)
    except Exception:  # noqa: BLE001
        return None


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[Redis, Depends(get_redis)]
ReqContext = Annotated[AuthContext, Depends(get_auth_context)]


def require_permission(permission: str):
    """`Depends(require_permission("course.create"))` ko'rinishida ishlatiladi."""

    async def _checker(
        user: CurrentUser,
        db: DbSession,
        redis: RedisClient,
    ) -> User:
        rbac = RBACService(db, redis)
        granted = await rbac.get_user_permissions(user.id)
        if not has_permission(granted, permission):
            raise ForbiddenError(f"Ruxsat yo'q: {permission}")
        return user

    return _checker


def require_role(role_code: str):
    async def _checker(user: CurrentUser, db: DbSession, redis: RedisClient) -> User:
        rbac = RBACService(db, redis)
        roles = await rbac.get_user_roles(user.id)
        if role_code not in roles:
            raise ForbiddenError(f"Rol talab qilinadi: {role_code}")
        return user

    return _checker

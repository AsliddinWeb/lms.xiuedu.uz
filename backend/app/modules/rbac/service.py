"""RBAC servisi — foydalanuvchi ruxsatlarini hisoblaydi va Redis'da keshlaydi.

Spec: docs/03-modules/02-users-rbac.md
"""

from __future__ import annotations

import json

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.rbac.models import Permission, Role, UserRole

_CACHE_PREFIX = "perms"
_CACHE_TTL = 300  # 5 daqiqa


def _matches(granted: str, required: str) -> bool:
    """Wildcard match: 'platform.*' → 'platform.users.create'."""
    if granted == required:
        return True
    if granted == "platform.*":
        return True  # Super admin — universal wildcard
    if granted.endswith(".*"):
        prefix = granted[:-2]
        return required.startswith(prefix + ".") or required == prefix
    return False


def has_permission(granted: list[str], required: str) -> bool:
    return any(_matches(g, required) for g in granted)


class RBACService:
    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self.db = db
        self.redis = redis

    async def get_user_permissions(self, user_id: int) -> list[str]:
        """Cache → DB. Permissionlar va rollar ro'yxatini qaytaradi."""
        key = f"{_CACHE_PREFIX}:{user_id}"
        cached = await self.redis.get(key)
        if cached:
            return list(json.loads(cached))

        perms = await self._load_permissions(user_id)
        await self.redis.set(key, json.dumps(perms), ex=_CACHE_TTL)
        return perms

    async def get_user_roles(self, user_id: int) -> list[str]:
        stmt = (
            select(Role.code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
            .distinct()
        )
        result = await self.db.execute(stmt)
        return [row[0] for row in result.all()]

    async def _load_permissions(self, user_id: int) -> list[str]:
        stmt = (
            select(Role)
            .options(selectinload(Role.permissions))
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        roles = result.scalars().unique().all()

        codes: set[str] = set()
        for role in roles:
            for perm in role.permissions:
                codes.add(perm.code)
        return sorted(codes)

    async def invalidate_user_cache(self, user_id: int) -> None:
        await self.redis.delete(f"{_CACHE_PREFIX}:{user_id}")

    async def assign_role(
        self,
        *,
        user_id: int,
        role_id: int,
        scope_type: str = "global",
        scope_id: int | None = None,
        granted_by: int | None = None,
    ) -> UserRole:
        # Idempotent — agar mavjud bo'lsa, mavjudini qaytaramiz
        existing = await self.db.execute(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id,
                UserRole.scope_type == scope_type,
                UserRole.scope_id.is_(scope_id),
            )
        )
        existing_ur = existing.scalar_one_or_none()
        if existing_ur is not None:
            return existing_ur

        ur = UserRole(
            user_id=user_id,
            role_id=role_id,
            scope_type=scope_type,
            scope_id=scope_id,
            granted_by=granted_by,
        )
        self.db.add(ur)
        await self.db.flush()
        await self.invalidate_user_cache(user_id)
        return ur

    async def unassign_role(
        self,
        *,
        user_id: int,
        role_id: int,
        scope_type: str = "global",
        scope_id: int | None = None,
    ) -> bool:
        result = await self.db.execute(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id,
                UserRole.scope_type == scope_type,
                UserRole.scope_id.is_(scope_id),
            )
        )
        ur = result.scalar_one_or_none()
        if ur is None:
            return False
        await self.db.delete(ur)
        await self.db.flush()
        await self.invalidate_user_cache(user_id)
        return True

    async def replace_user_roles(
        self,
        *,
        user_id: int,
        role_codes: list[str],
        scope_type: str = "global",
        scope_id: int | None = None,
        granted_by: int | None = None,
    ) -> list[UserRole]:
        """Foydalanuvchining global rollarini yangi ro'yxat bilan almashtirish."""
        # Mavjud global rollarni o'chirish
        existing = await self.db.execute(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.scope_type == scope_type,
                UserRole.scope_id.is_(scope_id),
            )
        )
        for ur in existing.scalars().all():
            await self.db.delete(ur)

        # Yangilarini biriktirish
        roles = await self.db.execute(select(Role).where(Role.code.in_(role_codes)))
        new_urs: list[UserRole] = []
        for role in roles.scalars().all():
            ur = UserRole(
                user_id=user_id,
                role_id=role.id,
                scope_type=scope_type,
                scope_id=scope_id,
                granted_by=granted_by,
            )
            self.db.add(ur)
            new_urs.append(ur)
        await self.db.flush()
        await self.invalidate_user_cache(user_id)
        return new_urs

    async def list_all_permissions(self) -> list[Permission]:
        result = await self.db.execute(
            select(Permission).order_by(Permission.category, Permission.code)
        )
        return list(result.scalars().all())

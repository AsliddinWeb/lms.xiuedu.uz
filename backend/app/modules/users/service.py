"""Users CRUD servisi (admin uchun).

Spec: docs/03-modules/02-users-rbac.md
"""

from __future__ import annotations

from datetime import UTC, datetime

from redis.asyncio import Redis
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.core.security import hash_password
from app.modules.auth.exceptions import UserAlreadyExistsError
from app.modules.rbac.models import Role, UserRole
from app.modules.rbac.service import RBACService
from app.modules.users.models import Profile, User
from app.modules.users.schemas import (
    UserCreateRequest,
    UserUpdateRequest,
)


class UsersService:
    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self.db = db
        self.redis = redis

    async def list_users(
        self,
        *,
        q: str | None = None,
        role_code: str | None = None,
        is_active: bool | None = None,
        tenant_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[User], int]:
        stmt = select(User).where(User.deleted_at.is_(None))

        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(User.email).like(like),
                    func.lower(User.full_name).like(like),
                    User.phone.like(f"%{q}%"),
                )
            )
        if is_active is not None:
            stmt = stmt.where(User.is_active.is_(is_active))
        if tenant_id is not None:
            stmt = stmt.where(User.tenant_id == tenant_id)
        if role_code:
            stmt = stmt.join(UserRole, UserRole.user_id == User.id).join(
                Role, Role.id == UserRole.role_id
            ).where(Role.code == role_code)

        total_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(total_stmt)).scalar_one()

        stmt = (
            stmt.options(
                selectinload(User.user_roles).selectinload(UserRole.role)
            )
            .order_by(desc(User.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        users = list(result.scalars().unique().all())
        return users, int(total)

    async def get_user(self, user_id: int) -> User:
        stmt = (
            select(User)
            .where(User.id == user_id, User.deleted_at.is_(None))
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            raise NotFoundError("Foydalanuvchi topilmadi")
        return user

    async def create_user(self, data: UserCreateRequest, granted_by: int | None) -> User:
        # Phase 10b — email optional. Duplicate check faqat email taqdim etilganda.
        email_normalized = data.email.lower().strip() if data.email else None
        if email_normalized:
            existing = await self.db.execute(
                select(User).where(User.email == email_normalized)
            )
            if existing.scalar_one_or_none():
                raise UserAlreadyExistsError()

        # HEMIS login takrorlanmasin
        if data.hemis_login:
            existing = await self.db.execute(
                select(User).where(User.hemis_login == data.hemis_login)
            )
            if existing.scalar_one_or_none():
                raise UserAlreadyExistsError()
        if data.hemis_id:
            existing = await self.db.execute(
                select(User).where(User.hemis_id == data.hemis_id)
            )
            if existing.scalar_one_or_none():
                raise UserAlreadyExistsError()

        # Email yo'q va HEMIS login yo'q bo'lsa — yaratib bo'lmaydi
        if email_normalized is None and not data.hemis_login:
            raise ValueError("Email yoki HEMIS login berilishi kerak")

        user = User(
            email=email_normalized,
            phone=data.phone,
            password_hash=hash_password(data.password),
            full_name=data.full_name.strip(),
            is_active=data.is_active,
            is_verified=data.is_verified,
            tenant_id=data.tenant_id,
            hemis_id=data.hemis_id,
            hemis_login=data.hemis_login,
        )
        user.profile = Profile()
        self.db.add(user)
        await self.db.flush()

        if data.role_codes:
            rbac = RBACService(self.db, self.redis)
            await rbac.replace_user_roles(
                user_id=user.id,
                role_codes=data.role_codes,
                granted_by=granted_by,
            )

        return await self.get_user(user.id)

    async def update_user(self, user_id: int, data: UserUpdateRequest) -> User:
        user = await self.get_user(user_id)
        update_data = data.model_dump(exclude_unset=True)
        for k, v in update_data.items():
            setattr(user, k, v)
        await self.db.flush()
        return await self.get_user(user_id)

    async def soft_delete_user(self, user_id: int) -> None:
        user = await self.get_user(user_id)
        user.deleted_at = datetime.now(UTC)
        user.is_active = False
        await self.db.flush()

    async def set_active(self, user_id: int, is_active: bool) -> User:
        user = await self.get_user(user_id)
        user.is_active = is_active
        if is_active:
            user.locked_until = None
            user.failed_login_attempts = 0
        await self.db.flush()
        return user

    async def reset_password(self, user_id: int, new_password: str) -> None:
        user = await self.get_user(user_id)
        user.password_hash = hash_password(new_password)
        user.failed_login_attempts = 0
        user.locked_until = None
        await self.db.flush()

"""Users CRUD endpointlari (admin uchun) + /me profile (Phase 2c).

Spec: docs/03-modules/02-users-rbac.md
"""

from __future__ import annotations

import secrets
from datetime import date as _date

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.exceptions import ValidationError
from app.core.storage import delete_object, object_key_from_url, upload_object
from app.modules.auth.dependencies import (
    CurrentUser,
    DbSession,
    RedisClient,
    require_permission,
)
from app.modules.rbac.models import Role, UserRole
from app.modules.rbac.schemas import RoleAssignmentRequest
from app.modules.rbac.service import RBACService, has_permission
from app.modules.users.models import Profile, User
from app.modules.users.schemas import (
    AvatarResponse,
    MePreferencesRequest,
    MeResponse,
    MeUpdateRequest,
    PaginatedUsers,
    ProfilePublic,
    UserCreateRequest,
    UserDetail,
    UserListItem,
    UserSetPasswordRequest,
    UserUpdateRequest,
)
from app.modules.users.service import UsersService

router = APIRouter()


# 2 MB
AVATAR_MAX_BYTES = 2 * 1024 * 1024
ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
ALLOWED_AVATAR_EXTS = {"jpg", "jpeg", "png", "webp"}


def _to_list_item(user: User) -> UserListItem:
    return UserListItem(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_2fa_enabled=user.is_2fa_enabled,
        last_login_at=user.last_login_at,
        tenant_id=user.tenant_id,
        roles=sorted({ur.role.code for ur in user.user_roles}),
        created_at=user.created_at,
    )


# ============================================================================
# /me — Profile (Phase 2c). MUHIM: /me marshrutlari /{user_id} dan oldin.
# ============================================================================


def _profile_public(profile: Profile | None) -> ProfilePublic | None:
    if profile is None:
        return None
    return ProfilePublic(
        # Phase 10b — alohida name fieldlar
        first_name=profile.first_name,
        last_name=profile.last_name,
        middle_name=profile.middle_name,
        pinfl=profile.pinfl,
        passport_series=profile.passport_series,
        passport_number=profile.passport_number,
        birthdate=profile.birthdate.isoformat() if profile.birthdate else None,
        gender=profile.gender,
        nationality=profile.nationality,
        address=profile.address,
        # Phase 10b — manzil hierarchy
        country=profile.country,
        region=profile.region,
        district=profile.district,
        # Phase 10b — ijtimoiy klassifikatsiya
        social_category=profile.social_category,
        poverty_level=profile.poverty_level,
        accommodation=profile.accommodation,
        # Phase 10b — akademik darajalar
        academic_degree=profile.academic_degree,
        academic_title=profile.academic_title,
        bio=profile.bio,
        language=profile.language,
        timezone=profile.timezone,
        notification_preferences=profile.notification_preferences or {},
    )


async def _load_me(db: DbSession, redis: RedisClient, user_id: int) -> tuple[User, list[str], list[str]]:
    stmt = (
        select(User)
        .where(User.id == user_id, User.deleted_at.is_(None))
        .options(
            selectinload(User.profile),
            selectinload(User.user_roles).selectinload(UserRole.role),
        )
    )
    result = await db.execute(stmt)
    user = result.scalar_one()
    rbac = RBACService(db, redis)
    roles = await rbac.get_user_roles(user.id)
    perms = await rbac.get_user_permissions(user.id)
    return user, roles, perms


def _build_me_response(user: User, roles: list[str], perms: list[str]) -> MeResponse:
    return MeResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_2fa_enabled=user.is_2fa_enabled,
        last_login_at=user.last_login_at,
        tenant_id=user.tenant_id,
        # Phase 10b — HEMIS identity
        hemis_id=user.hemis_id,
        hemis_login=user.hemis_login,
        hemis_last_synced_at=user.hemis_last_synced_at,
        # Phase 10b — student metadata
        group_id=user.group_id,
        current_semester_id=user.current_semester_id,
        education_form=user.education_form,
        payment_form=user.payment_form,
        student_status=user.student_status,
        # Phase 10b — employee metadata
        staff_position=user.staff_position,
        employment_form=user.employment_form,
        employment_staff=user.employment_staff,
        roles=roles,
        permissions=perms,
        profile=_profile_public(user.profile),
        created_at=user.created_at,
    )


@router.get("/me", response_model=MeResponse, summary="Joriy foydalanuvchi (full profile)")
async def get_me(
    me: CurrentUser, db: DbSession, redis: RedisClient
) -> MeResponse:
    user, roles, perms = await _load_me(db, redis, me.id)
    return _build_me_response(user, roles, perms)


@router.patch("/me", response_model=MeResponse, summary="O'z profilini yangilash")
async def update_me(
    data: MeUpdateRequest, me: CurrentUser, db: DbSession, redis: RedisClient
) -> MeResponse:
    update = data.model_dump(exclude_unset=True)
    user_fields = {k: v for k, v in update.items() if k in {"full_name", "phone"}}
    profile_fields = {k: v for k, v in update.items() if k not in user_fields}

    if user_fields:
        for k, v in user_fields.items():
            setattr(me, k, v)

    if profile_fields:
        # Profile mavjud emas bo'lsa yaratamiz
        if me.profile is None:
            me.profile = Profile(user_id=me.id)
            db.add(me.profile)
            await db.flush()

        # Birthdate parse + range
        if "birthdate" in profile_fields:
            bd = profile_fields["birthdate"]
            if bd in (None, ""):
                me.profile.birthdate = None
            else:
                try:
                    parsed = _date.fromisoformat(bd)
                except ValueError as exc:
                    raise ValidationError(
                        "birthdate YYYY-MM-DD formatida bo'lishi kerak"
                    ) from exc
                today = _date.today()
                if parsed > today:
                    raise ValidationError("birthdate kelajakda bo'lishi mumkin emas")
                if parsed.year < 1900:
                    raise ValidationError("birthdate 1900-yildan oldin bo'lishi mumkin emas")
                me.profile.birthdate = parsed
            del profile_fields["birthdate"]

        for k, v in profile_fields.items():
            setattr(me.profile, k, v)

    await db.commit()
    user, roles, perms = await _load_me(db, redis, me.id)
    return _build_me_response(user, roles, perms)


@router.patch(
    "/me/preferences",
    response_model=MeResponse,
    summary="Bildirishnoma sozlamalari (notification_preferences)",
)
async def update_me_preferences(
    data: MePreferencesRequest, me: CurrentUser, db: DbSession, redis: RedisClient
) -> MeResponse:
    if me.profile is None:
        me.profile = Profile(user_id=me.id)
        db.add(me.profile)
        await db.flush()
    me.profile.notification_preferences = data.notification_preferences
    await db.commit()
    user, roles, perms = await _load_me(db, redis, me.id)
    return _build_me_response(user, roles, perms)


@router.post(
    "/me/avatar",
    response_model=AvatarResponse,
    summary="Avatar yuklash (max 2 MB, jpg/png/webp)",
)
async def upload_avatar(
    me: CurrentUser,
    db: DbSession,
    file: UploadFile = File(..., description="Avatar fayl (jpg/png/webp)"),
) -> AvatarResponse:
    # Size limit
    contents = await file.read()
    if len(contents) > AVATAR_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Avatar hajmi 2 MB dan oshmasligi kerak (joriy: {len(contents)} bytes)",
        )

    # Content type
    ctype = (file.content_type or "").lower()
    if ctype not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Avatar formati qo'llab-quvvatlanmaydi: {ctype}. Ruxsat: jpg, png, webp",
        )

    # Extension
    filename = file.filename or "avatar"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    if ext not in ALLOWED_AVATAR_EXTS:
        ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(ctype, "jpg")

    # Eski avatar'ni o'chirish (agar bo'lsa)
    old_key = object_key_from_url(me.avatar_url)
    if old_key:
        delete_object(old_key)

    # Yangi key + upload
    object_name = f"avatars/{me.id}/{secrets.token_hex(8)}.{ext}"
    public_url = upload_object(
        object_name=object_name,
        data=contents,
        content_type=ctype,
    )

    me.avatar_url = public_url
    await db.commit()
    return AvatarResponse(avatar_url=public_url)


@router.delete(
    "/me/avatar", status_code=status.HTTP_204_NO_CONTENT, summary="Avatarni o'chirish"
)
async def delete_avatar(me: CurrentUser, db: DbSession) -> None:
    key = object_key_from_url(me.avatar_url)
    if key:
        delete_object(key)
    me.avatar_url = None
    await db.commit()


@router.get(
    "",
    response_model=PaginatedUsers,
    summary="Foydalanuvchilar ro'yxati (filter + pagination)",
)
async def list_users(
    db: DbSession,
    redis: RedisClient,
    _user: User = Depends(require_permission("users.read")),
    q: str | None = Query(None, description="Email/ism/telefon bo'yicha qidirish"),
    role: str | None = Query(None, description="Rol kodi bo'yicha filter"),
    is_active: bool | None = Query(None),
    tenant_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedUsers:
    # Multi-tenant scope enforcement: faqat platform.* (super_admin) erkin
    # tenant_id berishi mumkin. Boshqalar (otm_admin, dean, support) avtomatik
    # o'z `tenant_id`'siga yopib qo'yiladi — boshqa OTM userlarini ko'ra olmaydi.
    rbac = RBACService(db, redis)
    perms = await rbac.get_user_permissions(_user.id)
    if not has_permission(perms, "platform.*"):
        # Foydalanuvchining o'z tenant'iga avto-clamp
        tenant_id = _user.tenant_id

    service = UsersService(db, redis)
    items, total = await service.list_users(
        q=q,
        role_code=role,
        is_active=is_active,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedUsers(
        items=[_to_list_item(u) for u in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=UserDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi foydalanuvchi yaratish",
)
async def create_user(
    data: UserCreateRequest,
    db: DbSession,
    redis: RedisClient,
    actor: User = Depends(require_permission("users.manage")),
) -> UserDetail:
    service = UsersService(db, redis)
    user = await service.create_user(data, granted_by=actor.id)
    await db.commit()

    rbac = RBACService(db, redis)
    perms = await rbac.get_user_permissions(user.id)
    item = _to_list_item(user)
    return UserDetail(**item.model_dump(), permissions=perms)


@router.get("/{user_id}", response_model=UserDetail, summary="Foydalanuvchi tafsiloti")
async def get_user(
    user_id: int,
    db: DbSession,
    redis: RedisClient,
    _user: User = Depends(require_permission("users.read")),
) -> UserDetail:
    service = UsersService(db, redis)
    user = await service.get_user(user_id)
    rbac = RBACService(db, redis)
    perms = await rbac.get_user_permissions(user.id)
    item = _to_list_item(user)
    return UserDetail(**item.model_dump(), permissions=perms)


@router.patch("/{user_id}", response_model=UserDetail, summary="Foydalanuvchi ma'lumotlarini tahrirlash")
async def update_user(
    user_id: int,
    data: UserUpdateRequest,
    db: DbSession,
    redis: RedisClient,
    _user: User = Depends(require_permission("users.manage")),
) -> UserDetail:
    service = UsersService(db, redis)
    user = await service.update_user(user_id, data)
    await db.commit()
    rbac = RBACService(db, redis)
    perms = await rbac.get_user_permissions(user.id)
    item = _to_list_item(user)
    return UserDetail(**item.model_dump(), permissions=perms)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Foydalanuvchini soft-delete qilish",
)
async def delete_user(
    user_id: int,
    db: DbSession,
    redis: RedisClient,
    actor: User = Depends(require_permission("users.manage")),
) -> None:
    if user_id == actor.id:
        from app.core.exceptions import ConflictError

        raise ConflictError("O'z akkauntingizni o'chira olmaysiz")
    service = UsersService(db, redis)
    await service.soft_delete_user(user_id)
    await db.commit()


@router.post("/{user_id}/activate", response_model=UserDetail)
async def activate_user(
    user_id: int,
    db: DbSession,
    redis: RedisClient,
    _user: User = Depends(require_permission("users.manage")),
) -> UserDetail:
    service = UsersService(db, redis)
    user = await service.set_active(user_id, True)
    await db.commit()
    rbac = RBACService(db, redis)
    perms = await rbac.get_user_permissions(user.id)
    return UserDetail(**_to_list_item(user).model_dump(), permissions=perms)


@router.post("/{user_id}/deactivate", response_model=UserDetail)
async def deactivate_user(
    user_id: int,
    db: DbSession,
    redis: RedisClient,
    actor: User = Depends(require_permission("users.manage")),
) -> UserDetail:
    if user_id == actor.id:
        from app.core.exceptions import ConflictError

        raise ConflictError("O'z akkauntingizni nofaollashtira olmaysiz")
    service = UsersService(db, redis)
    user = await service.set_active(user_id, False)
    await db.commit()
    rbac = RBACService(db, redis)
    perms = await rbac.get_user_permissions(user.id)
    return UserDetail(**_to_list_item(user).model_dump(), permissions=perms)


@router.post("/{user_id}/set-password", status_code=status.HTTP_204_NO_CONTENT)
async def set_password(
    user_id: int,
    data: UserSetPasswordRequest,
    db: DbSession,
    redis: RedisClient,
    _user: User = Depends(require_permission("users.manage")),
) -> None:
    service = UsersService(db, redis)
    await service.reset_password(user_id, data.password)
    await db.commit()


@router.post("/{user_id}/roles", status_code=status.HTTP_204_NO_CONTENT)
async def assign_role(
    user_id: int,
    data: RoleAssignmentRequest,
    db: DbSession,
    redis: RedisClient,
    actor: User = Depends(require_permission("users.manage")),
) -> None:
    rbac = RBACService(db, redis)
    await rbac.assign_role(
        user_id=user_id,
        role_id=data.role_id,
        scope_type=data.scope_type,
        scope_id=data.scope_id,
        granted_by=actor.id,
    )
    await db.commit()


@router.delete("/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unassign_role(
    user_id: int,
    role_id: int,
    db: DbSession,
    redis: RedisClient,
    _user: User = Depends(require_permission("users.manage")),
) -> None:
    rbac = RBACService(db, redis)
    await rbac.unassign_role(user_id=user_id, role_id=role_id)
    await db.commit()


@router.put("/{user_id}/roles", status_code=status.HTTP_204_NO_CONTENT)
async def replace_roles(
    user_id: int,
    role_codes: list[str],
    db: DbSession,
    redis: RedisClient,
    actor: User = Depends(require_permission("users.manage")),
) -> None:
    """Foydalanuvchi rollarini ro'yxat bilan to'liq almashtirish."""
    # Mavjud rollarni tekshirish
    valid = await db.execute(select(Role.code).where(Role.code.in_(role_codes)))
    valid_codes = {r[0] for r in valid.all()}
    invalid = set(role_codes) - valid_codes
    if invalid:
        from app.core.exceptions import ValidationError

        raise ValidationError(f"Noma'lum rollar: {', '.join(sorted(invalid))}")

    rbac = RBACService(db, redis)
    await rbac.replace_user_roles(
        user_id=user_id, role_codes=role_codes, granted_by=actor.id
    )
    await db.commit()

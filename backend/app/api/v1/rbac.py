"""RBAC endpoint'lari: roles + permissions katalogi (admin read-only).

Spec: docs/03-modules/02-users-rbac.md
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.modules.auth.dependencies import DbSession, require_permission
from app.modules.rbac.models import Permission, Role
from app.modules.rbac.schemas import PermissionPublic, RolePublic

router = APIRouter()


@router.get(
    "/roles",
    response_model=list[RolePublic],
    summary="Tizimdagi barcha rollar (permissions bilan)",
)
async def list_roles(
    db: DbSession, _user=Depends(require_permission("users.read"))
) -> list[RolePublic]:
    stmt = select(Role).options(selectinload(Role.permissions)).order_by(Role.id)
    result = await db.execute(stmt)
    roles = result.scalars().unique().all()
    return [RolePublic.model_validate(r) for r in roles]


@router.get(
    "/permissions",
    response_model=list[PermissionPublic],
    summary="Permission katalogi",
)
async def list_permissions(
    db: DbSession, _user=Depends(require_permission("users.read"))
) -> list[PermissionPublic]:
    stmt = select(Permission).order_by(Permission.category, Permission.code)
    result = await db.execute(stmt)
    return [PermissionPublic.model_validate(p) for p in result.scalars().all()]

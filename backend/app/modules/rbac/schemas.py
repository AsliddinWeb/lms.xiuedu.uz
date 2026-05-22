"""RBAC Pydantic schemalar."""

from pydantic import BaseModel, ConfigDict


class PermissionPublic(BaseModel):
    id: int
    code: str
    name: str
    description: str | None = None
    category: str | None = None

    model_config = ConfigDict(from_attributes=True)


class RolePublic(BaseModel):
    id: int
    code: str
    name: str
    description: str | None = None
    is_system: bool
    tenant_id: int | None = None
    permissions: list[PermissionPublic] = []

    model_config = ConfigDict(from_attributes=True)


class RoleAssignmentRequest(BaseModel):
    role_id: int
    scope_type: str = "global"
    scope_id: int | None = None

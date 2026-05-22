"""RBAC modellari: Role, Permission, RolePermission, UserRole.

Spec: docs/03-modules/02-users-rbac.md, docs/01-overview/04-roles.md
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IDMixin, TimestampMixin


class Role(Base, IDMixin, TimestampMixin):
    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tenant_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    permissions: Mapped[list["Permission"]] = relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
        lazy="selectin",
    )
    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole",
        back_populates="role",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Role {self.code}>"


class Permission(Base, IDMixin):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), index=True, nullable=True)

    roles: Mapped[list[Role]] = relationship(
        "Role",
        secondary="role_permissions",
        back_populates="permissions",
    )

    def __repr__(self) -> str:
        return f"<Permission {self.code}>"


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "role_id", "scope_type", "scope_id", name="uq_user_role_scope"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )

    # Scope: 'global', 'org', 'faculty', 'department', 'course'
    scope_type: Mapped[str] = mapped_column(String(50), default="global", nullable=False)
    scope_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)

    granted_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User", back_populates="user_roles", foreign_keys=[user_id]
    )
    role: Mapped[Role] = relationship("Role", back_populates="user_roles")

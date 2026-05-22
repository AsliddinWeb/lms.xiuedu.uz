"""Organization (OTM) — multi-tenant root.

Spec: docs/03-modules/03-academic.md
559-qaror: 8-band (mamlakat ichida server), white-label uchun branding.
"""

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IDMixin, TimestampMixin


class Organization(Base, IDMixin, TimestampMixin):
    __tablename__ = "organizations"

    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Tashkilot turi: 'state' | 'private' | 'foreign'
    type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    license_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Rektor — foydalanuvchilarga link (FK ondelete=SET NULL: rektor o'chirilganda OTM o'chmasligi kerak)
    rector_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Kontakt
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # White-label
    domain: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    branding: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Organization {self.code}>"

"""Sertifikat modeli — Phase 11d."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IDMixin


class Certificate(Base, IDMixin):
    """Talaba kurs muvaffaqiyatli tugatganidagi sertifikat.

    `verification_code` — QR kod ichida kodlanadigan qisqa token. Public
    `/verify/{code}` endpoint orqali tekshiriladi.

    `pdf_path` — MinIO objektining yo'li, "certificates/{id}/{cert_number}.pdf".
    """

    __tablename__ = "certificates"
    __table_args__ = (
        Index(
            "ix_certificates_user_course",
            "user_id",
            "course_id",
            unique=True,
        ),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    course_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("courses.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    certificate_number: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True
    )
    verification_code: Mapped[str] = mapped_column(
        String(32), nullable=False, unique=True
    )
    score_percentage: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    pdf_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoke_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<Certificate id={self.id} number={self.certificate_number!r} "
            f"user={self.user_id} course={self.course_id}>"
        )

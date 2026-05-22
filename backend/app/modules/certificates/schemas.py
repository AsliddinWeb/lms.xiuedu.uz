"""Sertifikat Pydantic sxemalari — Phase 11d."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CertificatePublic(BaseModel):
    id: int
    user_id: int
    course_id: int
    certificate_number: str
    verification_code: str
    score_percentage: Decimal | None
    pdf_path: str | None
    issued_at: datetime
    revoked_at: datetime | None
    revoke_reason: str | None

    model_config = ConfigDict(from_attributes=True)


class CertificateMyItem(BaseModel):
    """My certificates ro'yxatida ko'rsatish uchun — kurs sarlavhasi bilan."""

    id: int
    certificate_number: str
    course_id: int
    course_title: str
    score_percentage: Decimal | None
    issued_at: datetime
    revoked_at: datetime | None
    pdf_url: str | None
    verification_url: str


class CertificateVerifyResponse(BaseModel):
    """Public verifikatsiya javobi — minimal ma'lumotlar.

    Talaba/kurs ismi ko'rsatiladi (verifikatsiya maqsadida), lekin sezgir
    PII ma'lumotlar (email, telefon) chiqarilmaydi.
    """

    valid: bool
    certificate_number: str | None = None
    student_name: str | None = None
    course_title: str | None = None
    issued_at: datetime | None = None
    revoked_at: datetime | None = None
    revoke_reason: str | None = None
    score_percentage: Decimal | None = None

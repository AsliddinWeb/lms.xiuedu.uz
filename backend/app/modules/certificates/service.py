"""Sertifikat servisi — Phase 11d.

Asosiy oqim:
    1. Talaba kursni tugatadi (Enrollment.completion_status = 'completed')
        -> `issue_certificate(db, user_id, course_id)` chaqiriladi (idempotent)
    2. PDF generatsiya qilinadi, MinIO'ga yuklanadi
    3. Verification_code random base32 token
    4. Public `/api/v1/verify/{code}` orqali sertifikat haqiqiyligini tekshirish

Sertifikat raqami formati: `XIU-{year}-{6 digit zero-padded id}`
Verification code: 16 ta belgi (base32, secrets.token_urlsafe asosida)
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.logging import get_logger
from app.core.storage import upload_object
from app.core.tenant import ensure_xiu_org
from app.modules.certificates.models import Certificate
from app.modules.certificates.pdf import render_certificate_pdf
from app.modules.courses.models import Course, Enrollment
from app.modules.organizations.models import Organization
from app.modules.users.models import User


async def _org_name(db: AsyncSession, course: Course) -> str:
    """OTM nomini DB'dan oladi (adminka tahrirlaydi). Hech qayerda hardcode emas."""
    org = None
    if course.organization_id is not None:
        org = await db.get(Organization, course.organization_id)
    if org is None:
        org = await ensure_xiu_org(db)
    return org.name

logger = get_logger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def _generate_verification_code() -> str:
    """16 ta belgili URL-safe random token."""
    return secrets.token_urlsafe(12)[:16]


def _build_certificate_number(cert_id: int, issued_at: datetime) -> str:
    return f"XIU-{issued_at.year}-{cert_id:06d}"


def _verification_url(code: str) -> str:
    """Public verifikatsiya sahifa URL'i (QR ichida kodlanadi)."""
    base = settings.APP_FRONTEND_URL.rstrip("/")
    return f"{base}/verify/{code}"


# ============================================================================
# Issue (idempotent)
# ============================================================================


async def issue_certificate(
    db: AsyncSession, *, user_id: int, course_id: int
) -> Certificate:
    """Kurs tugatilgan deb belgilangan talaba uchun sertifikat berish.

    - Agar sertifikat oldindan mavjud bo'lsa, mavjudini qaytaradi (idempotent).
    - Enrollment `completed` bo'lmasa ConflictError.
    """
    # Mavjudini topish
    existing = (
        await db.execute(
            select(Certificate).where(
                Certificate.user_id == user_id,
                Certificate.course_id == course_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None and existing.revoked_at is None:
        return existing

    enrollment = (
        await db.execute(
            select(Enrollment).where(
                Enrollment.user_id == user_id,
                Enrollment.course_id == course_id,
            )
        )
    ).scalar_one_or_none()
    if enrollment is None:
        raise NotFoundError("Talaba bu kursga yozilmagan")
    if enrollment.completion_status != "completed":
        raise ConflictError(
            "Sertifikat faqat kurs tugatilgandan keyin beriladi"
        )

    user = await db.get(User, user_id)
    course = await db.get(Course, course_id)
    if user is None or course is None:
        raise NotFoundError("Foydalanuvchi yoki kurs topilmadi")

    issued_at = _now()
    # Avval row yaratamiz id olish uchun (cert raqami id ga bog'liq)
    cert = Certificate(
        user_id=user_id,
        course_id=course_id,
        certificate_number="pending",
        verification_code=_generate_verification_code(),
        score_percentage=(
            Decimal(enrollment.final_grade)
            if enrollment.final_grade is not None
            else None
        ),
        issued_at=issued_at,
    )
    db.add(cert)
    await db.flush()

    cert.certificate_number = _build_certificate_number(cert.id, issued_at)
    await db.flush()

    # PDF generatsiya + MinIO'ga upload
    pdf_bytes = render_certificate_pdf(
        student_name=user.full_name,
        course_title=course.title,
        certificate_number=cert.certificate_number,
        issued_at=issued_at,
        verification_url=_verification_url(cert.verification_code),
        organization_name=await _org_name(db, course),
        score_percentage=(
            float(cert.score_percentage) if cert.score_percentage is not None else None
        ),
    )
    object_name = f"certificates/{cert.id}/{cert.certificate_number}.pdf"
    try:
        upload_object(
            object_name=object_name,
            data=pdf_bytes,
            content_type="application/pdf",
        )
        cert.pdf_path = object_name
    except Exception as exc:  # noqa: BLE001
        # PDF storage xatosi yozuvni o'chirib tashlamasin —
        # keyinroq qayta generatsiya qilish mumkin
        logger.warning(
            "certificate.pdf_upload_failed",
            cert_id=cert.id,
            error=str(exc),
        )
    await db.flush()

    # Phase 13.17 — talaba'ga bildirishnoma (xato bo'lsa yutamiz)
    try:
        from app.modules.notifications import service as notifications_service

        await notifications_service.notify_certificate_issued(
            db,
            user_id=user_id,
            certificate_id=cert.id,
            certificate_number=cert.certificate_number,
            course_title=course.title,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "certificate.notify_failed", cert_id=cert.id, error=str(exc)
        )

    return cert


async def regenerate_pdf(db: AsyncSession, cert_id: int) -> Certificate:
    """Sertifikat PDF'ini qayta yaratadi (admin/moderator amali)."""
    cert = await db.get(Certificate, cert_id)
    if cert is None:
        raise NotFoundError("Sertifikat topilmadi")
    user = await db.get(User, cert.user_id)
    course = await db.get(Course, cert.course_id)
    if user is None or course is None:
        raise NotFoundError("Foydalanuvchi yoki kurs topilmadi")

    pdf_bytes = render_certificate_pdf(
        student_name=user.full_name,
        course_title=course.title,
        certificate_number=cert.certificate_number,
        issued_at=cert.issued_at,
        verification_url=_verification_url(cert.verification_code),
        organization_name=await _org_name(db, course),
        score_percentage=(
            float(cert.score_percentage) if cert.score_percentage is not None else None
        ),
    )
    object_name = f"certificates/{cert.id}/{cert.certificate_number}.pdf"
    upload_object(
        object_name=object_name,
        data=pdf_bytes,
        content_type="application/pdf",
    )
    cert.pdf_path = object_name
    await db.flush()
    return cert


# ============================================================================
# Read
# ============================================================================


async def list_for_user(
    db: AsyncSession, user_id: int
) -> list[Certificate]:
    rows = (
        await db.execute(
            select(Certificate)
            .where(Certificate.user_id == user_id)
            .order_by(Certificate.issued_at.desc())
        )
    ).scalars().all()
    return list(rows)


async def get_by_id(
    db: AsyncSession, cert_id: int, *, requester_id: int
) -> Certificate:
    cert = await db.get(Certificate, cert_id)
    if cert is None:
        raise NotFoundError("Sertifikat topilmadi")
    if cert.user_id != requester_id:
        raise ForbiddenError("Bu sertifikatga kirish ruxsati yo'q")
    return cert


async def verify(
    db: AsyncSession, verification_code: str
) -> Certificate | None:
    """Public verifikatsiya — kod orqali sertifikat topadi.

    None qaytarsa: yo kod noto'g'ri, yo sertifikat mavjud emas. Bekor qilingan
    sertifikat qaytariladi (frontend revoked_at ni tekshirib status'ni
    ko'rsatadi).
    """
    cert = (
        await db.execute(
            select(Certificate).where(
                Certificate.verification_code == verification_code
            )
        )
    ).scalar_one_or_none()
    return cert


# ============================================================================
# Revoke
# ============================================================================


async def revoke(
    db: AsyncSession, cert_id: int, *, reason: str | None = None
) -> Certificate:
    cert = await db.get(Certificate, cert_id)
    if cert is None:
        raise NotFoundError("Sertifikat topilmadi")
    if cert.revoked_at is not None:
        raise ConflictError("Sertifikat allaqachon bekor qilingan")
    cert.revoked_at = _now()
    cert.revoke_reason = reason
    await db.flush()
    return cert

"""Sertifikat endpointlari — Phase 11d.

Routes:
    GET    /me/certificates                 — talaba o'z sertifikatlari ro'yxati
    GET    /me/certificates/{id}            — bitta sertifikat tafsiloti + presigned PDF URL
    GET    /me/certificates/{id}/pdf        — PDF presigned URL redirect
    GET    /verify/{code}                   — PUBLIC verifikatsiya (autentifikatsiyasiz)
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.storage import get_presigned_url
from app.modules.auth.dependencies import CurrentUser, DbSession
from app.modules.certificates import service as certificates_service
from app.modules.certificates.schemas import (
    CertificateMyItem,
    CertificateVerifyResponse,
)
from app.modules.courses.models import Course
from app.modules.users.models import User

router = APIRouter()


def _verification_url(code: str) -> str:
    base = settings.APP_FRONTEND_URL.rstrip("/")
    return f"{base}/verify/{code}"


def _pdf_presigned(pdf_path: str | None) -> str | None:
    if not pdf_path:
        return None
    return get_presigned_url(pdf_path, ttl_seconds=900)


# ============================================================================
# Authenticated — my certificates
# ============================================================================


@router.get(
    "/me/certificates",
    response_model=list[CertificateMyItem],
    tags=["certificates"],
)
async def list_my_certificates(
    db: DbSession, user: CurrentUser
) -> list[CertificateMyItem]:
    certs = await certificates_service.list_for_user(db, user.id)
    if not certs:
        return []
    course_ids = [c.course_id for c in certs]
    courses = {
        c.id: c
        for c in (
            await db.execute(select(Course).where(Course.id.in_(course_ids)))
        )
        .scalars()
        .all()
    }
    out: list[CertificateMyItem] = []
    for c in certs:
        course = courses.get(c.course_id)
        out.append(
            CertificateMyItem(
                id=c.id,
                certificate_number=c.certificate_number,
                course_id=c.course_id,
                course_title=course.title if course else "—",
                score_percentage=c.score_percentage,
                issued_at=c.issued_at,
                revoked_at=c.revoked_at,
                pdf_url=_pdf_presigned(c.pdf_path),
                verification_url=_verification_url(c.verification_code),
            )
        )
    return out


@router.get(
    "/me/certificates/{cert_id}",
    response_model=CertificateMyItem,
    tags=["certificates"],
)
async def get_my_certificate(
    cert_id: int, db: DbSession, user: CurrentUser
) -> CertificateMyItem:
    cert = await certificates_service.get_by_id(db, cert_id, requester_id=user.id)
    course = await db.get(Course, cert.course_id)
    return CertificateMyItem(
        id=cert.id,
        certificate_number=cert.certificate_number,
        course_id=cert.course_id,
        course_title=course.title if course else "—",
        score_percentage=cert.score_percentage,
        issued_at=cert.issued_at,
        revoked_at=cert.revoked_at,
        pdf_url=_pdf_presigned(cert.pdf_path),
        verification_url=_verification_url(cert.verification_code),
    )


@router.get(
    "/me/certificates/{cert_id}/pdf",
    tags=["certificates"],
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
)
async def download_my_certificate_pdf(
    cert_id: int, db: DbSession, user: CurrentUser
) -> Response:
    cert = await certificates_service.get_by_id(db, cert_id, requester_id=user.id)
    if not cert.pdf_path:
        # Yana bir marta generatsiya qilishga uringaymiz
        cert = await certificates_service.regenerate_pdf(db, cert.id)
        await db.commit()
    if not cert.pdf_path:
        raise NotFoundError("PDF mavjud emas")
    url = get_presigned_url(cert.pdf_path, ttl_seconds=900)
    return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


# ============================================================================
# Public — verification (no auth)
# ============================================================================


@router.get(
    "/verify/{code}",
    response_model=CertificateVerifyResponse,
    tags=["certificates", "public"],
)
async def verify_certificate(
    code: str, db: DbSession
) -> CertificateVerifyResponse:
    cert = await certificates_service.verify(db, code)
    if cert is None:
        return CertificateVerifyResponse(valid=False)
    user = await db.get(User, cert.user_id)
    course = await db.get(Course, cert.course_id)
    return CertificateVerifyResponse(
        valid=cert.revoked_at is None,
        certificate_number=cert.certificate_number,
        student_name=user.full_name if user else None,
        course_title=course.title if course else None,
        issued_at=cert.issued_at,
        revoked_at=cert.revoked_at,
        revoke_reason=cert.revoke_reason,
        score_percentage=cert.score_percentage,
    )

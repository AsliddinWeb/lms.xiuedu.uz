"""SCORM API endpointlar — Phase 11a.

Admin/pedagog:
    POST /scorm/packages/upload  (multipart: zip file + content_item_id)
    GET  /scorm/packages/{id}

Talaba:
    POST /scorm/packages/{id}/start   — yangi attempt yoki resume
    GET  /scorm/attempts/{id}         — attempt + cmi_data
    POST /scorm/attempts/{id}/commit  — batch CMI update
    POST /scorm/attempts/{id}/finish  — LMSFinish
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.config import settings
from app.core.exceptions import ForbiddenError
from app.modules.auth.dependencies import (
    CurrentUser,
    DbSession,
    require_permission,
)
from app.modules.scorm import service
from app.modules.scorm.schemas import (
    CmiCommitRequest,
    ScormAttemptPublic,
    ScormPackagePublic,
    StartAttemptResponse,
)
from app.modules.users.models import User

router = APIRouter(prefix="/scorm", tags=["scorm"])


def _build_launch_url(package_path: str, launch_url: str) -> str:
    """MinIO public URL ni quradi.

    `package_path` = 'scorm/{id}/' (bucket prefix)
    `launch_url` = 'shared/launchpage.html' (manifestdan)
    """
    base = (
        settings.MINIO_PUBLIC_URL.rstrip("/")
        if settings.MINIO_PUBLIC_URL
        else ""
    )
    bucket = settings.MINIO_BUCKET
    return f"{base}/{bucket}/{package_path}{launch_url}"


@router.post(
    "/packages/upload",
    response_model=ScormPackagePublic,
    summary="SCORM ZIP yuklash (admin/pedagog)",
)
async def upload_scorm(
    db: DbSession,
    user: CurrentUser,
    file: UploadFile = File(...),
    content_item_id: int = Form(...),
    _u: User = Depends(require_permission("content.create")),
) -> ScormPackagePublic:
    zip_bytes = await file.read()
    package = await service.upload_scorm_package(
        db,
        content_item_id=content_item_id,
        zip_bytes=zip_bytes,
        author_id=user.id,
    )
    await db.commit()
    payload = ScormPackagePublic.model_validate(package)
    payload.launch_full_url = _build_launch_url(package.package_path, package.launch_url)
    return payload


@router.get(
    "/packages/{package_id}",
    response_model=ScormPackagePublic,
    summary="SCORM paket ma'lumotlari",
)
async def get_scorm_package(
    package_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("content.read")),
) -> ScormPackagePublic:
    package = await service.get_package(db, package_id)
    payload = ScormPackagePublic.model_validate(package)
    payload.launch_full_url = _build_launch_url(package.package_path, package.launch_url)
    return payload


# ============================================================================
# Student attempts
# ============================================================================


@router.post(
    "/packages/{package_id}/start",
    response_model=StartAttemptResponse,
    summary="SCORM kurs boshlash (yangi attempt yoki resume)",
)
async def start_attempt(
    package_id: int,
    db: DbSession,
    user: CurrentUser,
    lesson_id: int | None = None,
    _u: User = Depends(require_permission("course.read")),
) -> StartAttemptResponse:
    package = await service.get_package(db, package_id)
    attempt = await service.get_or_create_attempt(
        db, package_id=package_id, user_id=user.id, lesson_id=lesson_id
    )
    await db.commit()
    pkg = ScormPackagePublic.model_validate(package)
    launch = _build_launch_url(package.package_path, package.launch_url)
    pkg.launch_full_url = launch
    return StartAttemptResponse(
        attempt=ScormAttemptPublic.model_validate(attempt),
        package=pkg,
        launch_full_url=launch,
    )


@router.get(
    "/attempts/{attempt_id}",
    response_model=ScormAttemptPublic,
    summary="SCORM attempt ma'lumotlari (CMI data bilan)",
)
async def get_attempt(
    attempt_id: int,
    db: DbSession,
    user: CurrentUser,
    _u: User = Depends(require_permission("course.read")),
) -> ScormAttemptPublic:
    attempt = await service.get_attempt(db, attempt_id)
    # Faqat o'z attempt'iga ruxsat (yoki content.read.all)
    if attempt.user_id != user.id:
        raise ForbiddenError("Boshqaning SCORM attempti'ga ruxsat yo'q")
    return ScormAttemptPublic.model_validate(attempt)


@router.post(
    "/attempts/{attempt_id}/commit",
    response_model=ScormAttemptPublic,
    summary="SCORM LMSCommit — CMI ma'lumotlarni saqlash",
)
async def commit_attempt(
    attempt_id: int,
    data: CmiCommitRequest,
    db: DbSession,
    user: CurrentUser,
    _u: User = Depends(require_permission("course.read")),
) -> ScormAttemptPublic:
    attempt = await service.get_attempt(db, attempt_id)
    if attempt.user_id != user.id:
        raise ForbiddenError("Boshqaning attempti'ni o'zgartirib bo'lmaydi")
    attempt = await service.commit_cmi(
        db, attempt_id=attempt_id, cmi_updates=data.cmi_updates
    )
    await db.commit()
    return ScormAttemptPublic.model_validate(attempt)


@router.post(
    "/attempts/{attempt_id}/finish",
    response_model=ScormAttemptPublic,
    summary="SCORM LMSFinish — attempt'ni yopish",
)
async def finish_attempt(
    attempt_id: int,
    db: DbSession,
    user: CurrentUser,
    _u: User = Depends(require_permission("course.read")),
) -> ScormAttemptPublic:
    attempt = await service.get_attempt(db, attempt_id)
    if attempt.user_id != user.id:
        raise ForbiddenError("Boshqaning attempti'ni yopib bo'lmaydi")
    attempt = await service.finish_attempt(db, attempt_id=attempt_id)
    await db.commit()
    return ScormAttemptPublic.model_validate(attempt)

"""SCORM service — Phase 11a.

Upload + extract + manifest parse + attempt management.
"""

from __future__ import annotations

import io
import mimetypes
import zipfile
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.core.storage import get_minio_client
from app.modules.content.models import ContentItem
from app.modules.scorm.manifest import ManifestParseError, parse_manifest
from app.modules.scorm.models import ScormAttempt, ScormPackage

logger = get_logger(__name__)


_MANIFEST_NAME = "imsmanifest.xml"
_MAX_PACKAGE_BYTES = 200 * 1024 * 1024  # 200 MB


async def upload_scorm_package(
    db: AsyncSession,
    *,
    content_item_id: int,
    zip_bytes: bytes,
    author_id: int,
) -> ScormPackage:
    """ZIP'ni MinIO'ga ochib chiqaradi, manifest parse qiladi, paket yaratadi."""
    if len(zip_bytes) > _MAX_PACKAGE_BYTES:
        raise ValidationError(
            f"SCORM ZIP juda katta: {len(zip_bytes)} > {_MAX_PACKAGE_BYTES}"
        )

    content = (
        await db.execute(
            select(ContentItem).where(ContentItem.id == content_item_id)
        )
    ).scalar_one_or_none()
    if content is None:
        raise NotFoundError(f"ContentItem id={content_item_id} topilmadi")

    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as exc:
        raise ValidationError(f"SCORM ZIP yaroqsiz: {exc}") from exc

    # Manifest topish — har joyda bo'lishi mumkin, lekin odatda root'da
    manifest_path = None
    for name in zf.namelist():
        if name.endswith(_MANIFEST_NAME) and "/" not in name.replace(
            _MANIFEST_NAME, ""
        ).rstrip("/"):
            manifest_path = name
            break
    if manifest_path is None:
        # Fallback: birinchi imsmanifest.xml ni topish
        for name in zf.namelist():
            if name.endswith(_MANIFEST_NAME):
                manifest_path = name
                break
    if manifest_path is None:
        raise ValidationError(
            "SCORM ZIP'da imsmanifest.xml topilmadi — bu SCORM paketi emas"
        )

    # Manifest folder prefix (e.g. "package_root/imsmanifest.xml" → "package_root/")
    manifest_prefix = manifest_path[: -len(_MANIFEST_NAME)]

    try:
        manifest = parse_manifest(zf.read(manifest_path))
    except ManifestParseError as exc:
        raise ValidationError(f"Manifest parse xatosi: {exc}") from exc

    # ScormPackage row yaratamiz (ID kerak — package_path uchun)
    package = ScormPackage(
        content_item_id=content_item_id,
        version=manifest.version,
        manifest_identifier=manifest.manifest_identifier,
        title=manifest.title or content.title,
        description=manifest.description,
        launch_url=manifest.launch_url,
        package_path="",  # quyida to'ldiriladi
        file_size=len(zip_bytes),
        mastery_score=manifest.mastery_score,
        uploaded_at=datetime.now(UTC),
    )
    db.add(package)
    await db.flush()  # id keldi

    # MinIO bucket prefix
    minio_prefix = f"scorm/{package.id}/"
    package.package_path = minio_prefix

    # Barcha fayllarni MinIO'ga yuklaymiz (manifest folder prefix'ni stripping bilan)
    client = get_minio_client()
    bucket = settings.MINIO_BUCKET
    uploaded_count = 0
    for name in zf.namelist():
        if name.endswith("/"):
            continue  # skip directory entries
        if not name.startswith(manifest_prefix):
            # Manifest prefix'sidan tashqarisidagi fayllar — odatda yo'q lekin
            # ehtiyot uchun ham yozamiz
            relative = name
        else:
            relative = name[len(manifest_prefix) :]
        if not relative:
            continue
        try:
            data = zf.read(name)
        except KeyError:
            continue
        mime, _ = mimetypes.guess_type(relative)
        client.put_object(
            bucket_name=bucket,
            object_name=f"{minio_prefix}{relative}",
            data=io.BytesIO(data),
            length=len(data),
            content_type=mime or "application/octet-stream",
        )
        uploaded_count += 1

    logger.info(
        "scorm.upload.done",
        package_id=package.id,
        files=uploaded_count,
        version=manifest.version,
    )

    # Content item type'ni 'scorm' ga belgilash
    content.type = "scorm"
    content.file_url = (
        f"{settings.MINIO_PUBLIC_URL.rstrip('/')}/{bucket}/{minio_prefix}{manifest.launch_url}"
        if settings.MINIO_PUBLIC_URL
        else f"/{bucket}/{minio_prefix}{manifest.launch_url}"
    )
    content.file_size = len(zip_bytes)
    content.mime_type = "application/zip"

    await db.flush()
    return package


async def get_package(db: AsyncSession, package_id: int) -> ScormPackage:
    p = (
        await db.execute(
            select(ScormPackage).where(ScormPackage.id == package_id)
        )
    ).scalar_one_or_none()
    if p is None:
        raise NotFoundError(f"SCORM paket id={package_id} topilmadi")
    return p


async def get_or_create_attempt(
    db: AsyncSession, *, package_id: int, user_id: int, lesson_id: int | None = None
) -> ScormAttempt:
    """Joriy attempt'ni qaytaradi yoki yangi yaratadi.

    Agar oxirgi attempt 'in_progress' bo'lsa — uni resume qiladi (CMI saqlanadi).
    Aks holda yangi attempt_number = oxirgi+1 yaratiladi.
    """
    last = (
        await db.execute(
            select(ScormAttempt)
            .where(
                ScormAttempt.user_id == user_id,
                ScormAttempt.package_id == package_id,
            )
            .order_by(desc(ScormAttempt.attempt_number))
            .limit(1)
        )
    ).scalar_one_or_none()

    if last is not None and last.status == "in_progress":
        # Resume
        last.last_accessed_at = datetime.now(UTC)
        await db.flush()
        return last

    next_num = (last.attempt_number + 1) if last else 1
    attempt = ScormAttempt(
        user_id=user_id,
        package_id=package_id,
        lesson_id=lesson_id,
        attempt_number=next_num,
        status="in_progress",
        cmi_data={},
        started_at=datetime.now(UTC),
        last_accessed_at=datetime.now(UTC),
    )
    db.add(attempt)
    await db.flush()
    return attempt


async def commit_cmi(
    db: AsyncSession,
    *,
    attempt_id: int,
    cmi_updates: dict[str, Any],
) -> ScormAttempt:
    """SCORM iframe `LMSSetValue` + `LMSCommit` chaqiruvlari natijasini saqlash.

    `cmi_updates` ko'p kalitli dict bo'lishi mumkin — bir yo'la barcha
    SetValue chaqiruvlarini batch saqlaymiz. Cached numeric/status fieldlar
    `cmi.core.lesson_status`, `cmi.core.score.raw`, va h.k.dan derivate qilinadi.
    """
    attempt = (
        await db.execute(
            select(ScormAttempt).where(ScormAttempt.id == attempt_id)
        )
    ).scalar_one_or_none()
    if attempt is None:
        raise NotFoundError(f"SCORM attempt id={attempt_id} topilmadi")

    data = dict(attempt.cmi_data or {})
    data.update(cmi_updates)
    attempt.cmi_data = data

    # Cached fields — SCORM 1.2 va 2004 schema'lari
    status_val = data.get("cmi.core.lesson_status") or data.get(
        "cmi.completion_status"
    )
    if status_val:
        # 1.2: 'passed' | 'completed' | 'failed' | 'incomplete' | 'browsed' | 'not attempted'
        # 2004: 'completed' | 'incomplete' | 'not attempted' | 'unknown'
        if status_val in ("passed", "completed"):
            attempt.status = "completed"
            if attempt.completed_at is None:
                attempt.completed_at = datetime.now(UTC)
        elif status_val == "failed":
            attempt.status = "failed"
        elif status_val == "browsed":
            attempt.status = "browsed"
        else:
            attempt.status = "in_progress"

    # Score (raw / scaled)
    raw = data.get("cmi.core.score.raw") or data.get("cmi.score.raw")
    if raw is not None:
        try:
            attempt.score_raw = Decimal(str(raw))
        except (ValueError, ArithmeticError):
            pass
    score_min = data.get("cmi.core.score.min") or data.get("cmi.score.min")
    if score_min is not None:
        try:
            attempt.score_min = Decimal(str(score_min))
        except (ValueError, ArithmeticError):
            pass
    score_max = data.get("cmi.core.score.max") or data.get("cmi.score.max")
    if score_max is not None:
        try:
            attempt.score_max = Decimal(str(score_max))
        except (ValueError, ArithmeticError):
            pass

    # Time
    total = data.get("cmi.core.total_time") or data.get("cmi.total_time")
    if total:
        attempt.total_time = str(total)
    session = data.get("cmi.core.session_time") or data.get("cmi.session_time")
    if session:
        attempt.session_time = str(session)

    # Bookmark + suspend
    bookmark = data.get("cmi.core.lesson_location") or data.get("cmi.location")
    if bookmark is not None:
        attempt.bookmark = str(bookmark)[:500]
    suspend = data.get("cmi.suspend_data")
    if suspend is not None:
        attempt.suspend_data = str(suspend)

    attempt.last_accessed_at = datetime.now(UTC)
    await db.flush()
    return attempt


async def finish_attempt(
    db: AsyncSession, *, attempt_id: int
) -> ScormAttempt:
    """`LMSFinish` chaqiruv — attempt'ni yopish."""
    attempt = await db.get(ScormAttempt, attempt_id)
    if attempt is None:
        raise NotFoundError(f"SCORM attempt id={attempt_id} topilmadi")
    # Status hali in_progress bo'lsa — incomplete deb belgilaymiz
    if attempt.status == "in_progress":
        attempt.status = "incomplete"
    if attempt.completed_at is None:
        attempt.completed_at = datetime.now(UTC)
    attempt.last_accessed_at = datetime.now(UTC)
    await db.flush()
    return attempt


async def get_attempt(db: AsyncSession, attempt_id: int) -> ScormAttempt:
    a = await db.get(ScormAttempt, attempt_id)
    if a is None:
        raise NotFoundError(f"SCORM attempt id={attempt_id} topilmadi")
    return a


async def list_user_attempts(
    db: AsyncSession, *, user_id: int, package_id: int
) -> list[ScormAttempt]:
    res = await db.execute(
        select(ScormAttempt)
        .where(
            ScormAttempt.user_id == user_id,
            ScormAttempt.package_id == package_id,
        )
        .order_by(ScormAttempt.attempt_number.desc())
    )
    return list(res.scalars().all())

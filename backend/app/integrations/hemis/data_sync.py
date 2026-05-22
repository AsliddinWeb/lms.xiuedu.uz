"""HEMIS data sync — Phase 10f.

HEMIS Backend API (`/v1/data/*`) orqali talaba/o'qituvchi/fakultet/guruh
ma'lumotlarini OTM admin tomonidan toptirib olinadi va bizning DB'ga yoziladi.

Sync turlari:
    - `sync_students`     — `/v1/data/student-list` → upsert_student
    - `sync_employees`    — `/v1/data/employee-list` → upsert_employee
    - `sync_departments`  — `/v1/data/department-list` → Faculty
    - `sync_groups`       — `/v1/data/group-list` → AcademicGroup
    - `sync_curricula`    — `/v1/data/curriculum-list` → Curriculum

Har sync:
  1. HemisSyncLog row yaratiladi (status='pending')
  2. HEMIS Backend API'dan paginatsiya bilan ma'lumotlar olinadi
  3. Har element uchun tegishli upsert_* helper chaqiriladi
  4. Yutgan/o'tkazib yuborilgan/xato sonlari yiqilib log'ga yoziladi
  5. Final status: 'success' yoki 'failed'

`HEMIS_SYNC_ENABLED=False` (default) bo'lsa, log 'skipped' bilan yoziladi.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.integrations.hemis.client import HemisClient, HemisError
from app.integrations.hemis.models import HemisSyncLog
from app.modules.academic.models import AcademicGroup, Faculty
from app.modules.users.hemis_sync import upsert_employee, upsert_student

logger = get_logger(__name__)


class SyncResult(TypedDict):
    log_id: int
    sync_type: str
    status: str  # 'success' | 'failed' | 'skipped'
    upserted: int
    failed: int
    total: int
    last_error: str | None


# ============================================================================
# Internal helpers
# ============================================================================


async def _create_log(
    db: AsyncSession, sync_type: str, payload: dict | None = None
) -> HemisSyncLog:
    log = HemisSyncLog(
        sync_type=sync_type,
        target_id=None,
        status="pending",
        attempts=0,
        payload=payload,
    )
    db.add(log)
    await db.flush()
    return log


async def _finalize_log(
    log: HemisSyncLog,
    *,
    status: str,
    upserted: int,
    failed: int,
    total: int,
    last_error: str | None = None,
) -> None:
    log.status = status
    log.attempts = (log.attempts or 0) + 1
    log.response = {
        "upserted": upserted,
        "failed": failed,
        "total": total,
    }
    log.last_error = last_error
    log.completed_at = datetime.now(UTC)


def _build_result(
    log: HemisSyncLog,
    *,
    upserted: int = 0,
    failed: int = 0,
    total: int = 0,
    last_error: str | None = None,
) -> SyncResult:
    return {
        "log_id": log.id,
        "sync_type": log.sync_type,
        "status": log.status,
        "upserted": upserted,
        "failed": failed,
        "total": total,
        "last_error": last_error,
    }


# ============================================================================
# Sync: Students
# ============================================================================


async def sync_students(
    db: AsyncSession, *, page_size: int = 100, max_pages: int = 100
) -> SyncResult:
    """`/v1/data/student-list` → User+Profile upsert.

    Paginatsiya: max_pages × page_size.
    """
    log = await _create_log(db, "student_list")

    if not settings.HEMIS_SYNC_ENABLED:
        await _finalize_log(
            log, status="skipped", upserted=0, failed=0, total=0,
            last_error="HEMIS_SYNC_ENABLED=False",
        )
        await db.flush()
        return _build_result(log, last_error="sync disabled")

    upserted = 0
    failed = 0
    total = 0
    last_error: str | None = None

    try:
        async with HemisClient() as client:
            for page in range(1, max_pages + 1):
                resp = await client.student_list(page=page, limit=page_size)
                items: list[dict[str, Any]] = resp.get("items", [])
                if not items:
                    break
                total += len(items)
                for item in items:
                    try:
                        await upsert_student(db, item)
                        upserted += 1
                    except Exception as exc:  # noqa: BLE001
                        failed += 1
                        last_error = f"item id={item.get('id')}: {exc}"
                        logger.warning(
                            "hemis_sync.student.failed", item_id=item.get("id"), error=str(exc)
                        )
                # pagination tugadi
                pagination = resp.get("pagination", {})
                if page >= pagination.get("pageCount", page):
                    break
        status = "failed" if failed and not upserted else "success"
        await _finalize_log(
            log, status=status, upserted=upserted, failed=failed, total=total,
            last_error=last_error,
        )
    except HemisError as exc:
        await _finalize_log(
            log, status="failed", upserted=upserted, failed=failed, total=total,
            last_error=f"HEMIS error: {exc}",
        )
        last_error = str(exc)
        logger.error("hemis_sync.students.fatal", error=str(exc))

    await db.flush()
    return _build_result(
        log, upserted=upserted, failed=failed, total=total, last_error=last_error
    )


# ============================================================================
# Sync: Employees
# ============================================================================


async def sync_employees(
    db: AsyncSession, *, page_size: int = 100, max_pages: int = 50
) -> SyncResult:
    log = await _create_log(db, "employee_list")

    if not settings.HEMIS_SYNC_ENABLED:
        await _finalize_log(
            log, status="skipped", upserted=0, failed=0, total=0,
            last_error="HEMIS_SYNC_ENABLED=False",
        )
        await db.flush()
        return _build_result(log, last_error="sync disabled")

    upserted = 0
    failed = 0
    total = 0
    last_error: str | None = None

    try:
        async with HemisClient() as client:
            for page in range(1, max_pages + 1):
                resp = await client.employee_list(page=page, limit=page_size)
                items: list[dict[str, Any]] = resp.get("items", [])
                if not items:
                    break
                total += len(items)
                for item in items:
                    try:
                        await upsert_employee(db, item)
                        upserted += 1
                    except Exception as exc:  # noqa: BLE001
                        failed += 1
                        last_error = f"item id={item.get('id')}: {exc}"
                        logger.warning(
                            "hemis_sync.employee.failed",
                            item_id=item.get("id"),
                            error=str(exc),
                        )
                pagination = resp.get("pagination", {})
                if page >= pagination.get("pageCount", page):
                    break
        status = "failed" if failed and not upserted else "success"
        await _finalize_log(
            log, status=status, upserted=upserted, failed=failed, total=total,
            last_error=last_error,
        )
    except HemisError as exc:
        await _finalize_log(
            log, status="failed", upserted=upserted, failed=failed, total=total,
            last_error=f"HEMIS error: {exc}",
        )
        last_error = str(exc)
        logger.error("hemis_sync.employees.fatal", error=str(exc))

    await db.flush()
    return _build_result(
        log, upserted=upserted, failed=failed, total=total, last_error=last_error
    )


# ============================================================================
# Sync: Departments (HEMIS Department → bizning Faculty)
# ============================================================================


async def _upsert_faculty_from_hemis(
    db: AsyncSession, data: dict[str, Any]
) -> Faculty:
    """HEMIS Department dict → Faculty upsert."""
    hemis_id = data["id"]
    fac = (
        await db.execute(select(Faculty).where(Faculty.hemis_id == hemis_id))
    ).scalar_one_or_none()

    structure_type = None
    locality_type = None
    if isinstance(data.get("structureType"), dict):
        structure_type = data["structureType"].get("code")
    if isinstance(data.get("localityType"), dict):
        locality_type = data["localityType"].get("code")

    from app.core.tenant import get_xiu_org_id

    if fac is None:
        # Yangi Faculty — XIU organization id
        org_id = await get_xiu_org_id(db)
        fac = Faculty(
            organization_id=org_id,
            code=data.get("code") or f"hemis-{hemis_id}",
            name=data["name"],
            hemis_id=hemis_id,
            hemis_code=data.get("code"),
            hemis_parent_id=data.get("parent"),
            structure_type=structure_type,
            locality_type=locality_type,
            is_active=bool(data.get("active", True)),
        )
        db.add(fac)
        await db.flush()
    else:
        fac.name = data["name"]
        fac.hemis_code = data.get("code") or fac.hemis_code
        fac.hemis_parent_id = data.get("parent")
        if structure_type:
            fac.structure_type = structure_type
        if locality_type:
            fac.locality_type = locality_type
        fac.is_active = bool(data.get("active", True))
    return fac


async def sync_departments(db: AsyncSession) -> SyncResult:
    log = await _create_log(db, "department_list")

    if not settings.HEMIS_SYNC_ENABLED:
        await _finalize_log(
            log, status="skipped", upserted=0, failed=0, total=0,
            last_error="HEMIS_SYNC_ENABLED=False",
        )
        await db.flush()
        return _build_result(log, last_error="sync disabled")

    upserted = 0
    failed = 0
    total = 0
    last_error: str | None = None

    try:
        async with HemisClient() as client:
            items: list[dict[str, Any]] = await client.department_list()
        total = len(items)
        for item in items:
            try:
                await _upsert_faculty_from_hemis(db, item)
                upserted += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                last_error = f"item id={item.get('id')}: {exc}"
                logger.warning(
                    "hemis_sync.department.failed",
                    item_id=item.get("id"),
                    error=str(exc),
                )
        status = "failed" if failed and not upserted else "success"
        await _finalize_log(
            log, status=status, upserted=upserted, failed=failed, total=total,
            last_error=last_error,
        )
    except HemisError as exc:
        await _finalize_log(
            log, status="failed", upserted=upserted, failed=failed, total=total,
            last_error=f"HEMIS error: {exc}",
        )
        last_error = str(exc)

    await db.flush()
    return _build_result(
        log, upserted=upserted, failed=failed, total=total, last_error=last_error
    )


# ============================================================================
# Sync: Groups
# ============================================================================


async def _upsert_group_from_hemis(
    db: AsyncSession, data: dict[str, Any]
) -> AcademicGroup:
    hemis_id = data["id"]
    grp = (
        await db.execute(
            select(AcademicGroup).where(AcademicGroup.hemis_id == hemis_id)
        )
    ).scalar_one_or_none()

    edu_lang = None
    if isinstance(data.get("educationLang"), dict):
        edu_lang = data["educationLang"].get("code")

    # Faculty linkage (HEMIS group.department → bizning faculty.hemis_id)
    faculty_id = None
    dep_hemis_id = data.get("department")
    if isinstance(dep_hemis_id, dict):
        dep_hemis_id = dep_hemis_id.get("id")
    if dep_hemis_id:
        fac = (
            await db.execute(select(Faculty).where(Faculty.hemis_id == dep_hemis_id))
        ).scalar_one_or_none()
        if fac:
            faculty_id = fac.id

    if grp is None:
        grp = AcademicGroup(
            hemis_id=hemis_id,
            name=data.get("name", f"group-{hemis_id}"),
            education_lang=edu_lang,
            faculty_id=faculty_id,
            is_active=True,
            hemis_last_synced_at=datetime.now(UTC),
        )
        db.add(grp)
        await db.flush()
    else:
        grp.name = data.get("name") or grp.name
        if edu_lang:
            grp.education_lang = edu_lang
        if faculty_id:
            grp.faculty_id = faculty_id
        grp.hemis_last_synced_at = datetime.now(UTC)
    return grp


async def sync_groups(db: AsyncSession) -> SyncResult:
    log = await _create_log(db, "group_list")

    if not settings.HEMIS_SYNC_ENABLED:
        await _finalize_log(
            log, status="skipped", upserted=0, failed=0, total=0,
            last_error="HEMIS_SYNC_ENABLED=False",
        )
        await db.flush()
        return _build_result(log, last_error="sync disabled")

    upserted = 0
    failed = 0
    total = 0
    last_error: str | None = None

    try:
        async with HemisClient() as client:
            items: list[dict[str, Any]] = await client.group_list()
        total = len(items)
        for item in items:
            try:
                await _upsert_group_from_hemis(db, item)
                upserted += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                last_error = f"item id={item.get('id')}: {exc}"
                logger.warning(
                    "hemis_sync.group.failed", item_id=item.get("id"), error=str(exc)
                )
        status = "failed" if failed and not upserted else "success"
        await _finalize_log(
            log, status=status, upserted=upserted, failed=failed, total=total,
            last_error=last_error,
        )
    except HemisError as exc:
        await _finalize_log(
            log, status="failed", upserted=upserted, failed=failed, total=total,
            last_error=f"HEMIS error: {exc}",
        )
        last_error = str(exc)

    await db.flush()
    return _build_result(
        log, upserted=upserted, failed=failed, total=total, last_error=last_error
    )


# ============================================================================
# Public dispatcher
# ============================================================================

# Mavjud sync turlari
SUPPORTED_SYNC_TYPES = ("students", "employees", "departments", "groups")


async def run_sync(db: AsyncSession, entity: str) -> SyncResult:
    """Universal dispatcher — admin API'dan ishlatiladi.

    Tartib (groups dan oldin departments — FK uchun):
        departments → groups → students → employees
    """
    if entity == "students":
        return await sync_students(db)
    if entity == "employees":
        return await sync_employees(db)
    if entity == "departments":
        return await sync_departments(db)
    if entity == "groups":
        return await sync_groups(db)
    if entity == "all":
        # Tartibga muvofiq cascade sync
        results = {}
        for e in ("departments", "groups", "students", "employees"):
            results[e] = await run_sync(db, e)
        # Eng oxirgi resultni qaytaramiz (umumiy log id sifatida)
        return results["employees"]
    raise ValueError(f"Unknown sync entity: {entity}")

"""Academic CRUD services — Faculty, Department, Specialty, Subject, Curriculum, AcademicCalendar.

559-qaror validatsiyalari schemalarda (Pydantic) bajariladi; bu service qatlami DB
operatsiyalari va biznes-mantiqi (multi-tenant scope, curriculum clone va h.k.) uchun.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.academic.models import (
    AcademicCalendar,
    Curriculum,
    CurriculumSubject,
    Department,
    Faculty,
    Specialty,
    Subject,
    SubjectPrerequisite,
)
from app.modules.academic.schemas import (
    AcademicCalendarCreateRequest,
    AcademicCalendarUpdateRequest,
    CurriculumCreateRequest,
    CurriculumUpdateRequest,
    DepartmentCreateRequest,
    DepartmentUpdateRequest,
    FacultyCreateRequest,
    FacultyUpdateRequest,
    SpecialtyCreateRequest,
    SpecialtyUpdateRequest,
    SubjectCreateRequest,
    SubjectUpdateRequest,
)
from app.modules.organizations.models import Organization
from app.modules.users.models import User


def _now() -> datetime:
    return datetime.now(UTC)


def _is_super_admin(user: User, user_roles: list[str]) -> bool:
    return "super_admin" in user_roles


# ============================================================================
# Organization (super admin'gina yarata oladi)
# ============================================================================


async def list_organizations(
    db: AsyncSession, *, q: str | None, page: int, page_size: int
) -> tuple[list[Organization], int]:
    stmt = select(Organization)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Organization.code).like(like),
                func.lower(Organization.name).like(like),
            )
        )
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.order_by(Organization.id).offset((page - 1) * page_size).limit(page_size)
    items = list((await db.execute(stmt)).scalars().all())
    return items, int(total)


async def get_organization(db: AsyncSession, org_id: int) -> Organization:
    org = await db.get(Organization, org_id)
    if org is None:
        raise NotFoundError("Universitet topilmadi")
    return org


async def create_organization(db: AsyncSession, data: dict[str, Any]) -> Organization:
    # Code uniqueness check
    existing = await db.execute(select(Organization).where(Organization.code == data["code"]))
    if existing.scalar_one_or_none():
        raise ConflictError(f"Universitet kodi '{data['code']}' band")
    org = Organization(**data)
    db.add(org)
    await db.flush()
    return org


async def update_organization(
    db: AsyncSession, org_id: int, data: dict[str, Any]
) -> Organization:
    org = await get_organization(db, org_id)
    for k, v in data.items():
        setattr(org, k, v)
    await db.flush()
    return org


# ============================================================================
# Faculty
# ============================================================================


async def list_faculties(
    db: AsyncSession,
    *,
    organization_id: int | None,
    is_active: bool | None,
    q: str | None,
    page: int,
    page_size: int,
) -> tuple[list[Faculty], int]:
    stmt = select(Faculty)
    if organization_id is not None:
        stmt = stmt.where(Faculty.organization_id == organization_id)
    if is_active is not None:
        stmt = stmt.where(Faculty.is_active.is_(is_active))
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(func.lower(Faculty.code).like(like), func.lower(Faculty.name).like(like))
        )
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.order_by(Faculty.id).offset((page - 1) * page_size).limit(page_size)
    items = list((await db.execute(stmt)).scalars().all())
    return items, int(total)


async def get_faculty(db: AsyncSession, faculty_id: int) -> Faculty:
    f = await db.get(Faculty, faculty_id)
    if f is None:
        raise NotFoundError("Fakultet topilmadi")
    return f


async def create_faculty(db: AsyncSession, data: FacultyCreateRequest) -> Faculty:
    from app.core.tenant import get_xiu_org_id

    # Single-tenant: organization_id berilmagan bo'lsa avto XIU
    payload = data.model_dump()
    if payload.get("organization_id") is None:
        payload["organization_id"] = await get_xiu_org_id(db)

    if (await db.get(Organization, payload["organization_id"])) is None:
        raise NotFoundError("Universitet topilmadi")

    # Org+code uniqueness
    dup = await db.execute(
        select(Faculty).where(
            Faculty.organization_id == payload["organization_id"],
            Faculty.code == data.code,
        )
    )
    if dup.scalar_one_or_none():
        raise ConflictError(f"Fakultet '{data.code}' kodi bilan mavjud")
    f = Faculty(**payload)
    db.add(f)
    await db.flush()
    return f


async def update_faculty(
    db: AsyncSession, faculty_id: int, data: FacultyUpdateRequest
) -> Faculty:
    f = await get_faculty(db, faculty_id)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(f, k, v)
    await db.flush()
    return f


async def delete_faculty(db: AsyncSession, faculty_id: int) -> None:
    f = await get_faculty(db, faculty_id)
    await db.delete(f)
    await db.flush()


# ============================================================================
# Department
# ============================================================================


async def list_departments(
    db: AsyncSession,
    *,
    faculty_id: int | None,
    organization_id: int | None,
    is_active: bool | None,
    q: str | None,
    page: int,
    page_size: int,
) -> tuple[list[Department], int]:
    stmt = select(Department)
    if faculty_id is not None:
        stmt = stmt.where(Department.faculty_id == faculty_id)
    if organization_id is not None:
        stmt = stmt.join(Faculty, Faculty.id == Department.faculty_id).where(
            Faculty.organization_id == organization_id
        )
    if is_active is not None:
        stmt = stmt.where(Department.is_active.is_(is_active))
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Department.code).like(like),
                func.lower(Department.name).like(like),
            )
        )
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.order_by(Department.id).offset((page - 1) * page_size).limit(page_size)
    items = list((await db.execute(stmt)).scalars().all())
    return items, int(total)


async def get_department(db: AsyncSession, dep_id: int) -> Department:
    d = await db.get(Department, dep_id)
    if d is None:
        raise NotFoundError("Kafedra topilmadi")
    return d


async def create_department(db: AsyncSession, data: DepartmentCreateRequest) -> Department:
    if (await db.get(Faculty, data.faculty_id)) is None:
        raise NotFoundError("Tanlangan fakultet topilmadi")
    dup = await db.execute(
        select(Department).where(
            Department.faculty_id == data.faculty_id, Department.code == data.code
        )
    )
    if dup.scalar_one_or_none():
        raise ConflictError(f"Bu fakultetda kafedra '{data.code}' kodi bilan mavjud")
    d = Department(**data.model_dump())
    db.add(d)
    await db.flush()
    return d


async def update_department(
    db: AsyncSession, dep_id: int, data: DepartmentUpdateRequest
) -> Department:
    d = await get_department(db, dep_id)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(d, k, v)
    await db.flush()
    return d


async def delete_department(db: AsyncSession, dep_id: int) -> None:
    d = await get_department(db, dep_id)
    await db.delete(d)
    await db.flush()


# ============================================================================
# Specialty (559-qaror 14 va 15-band)
# ============================================================================


async def list_specialties(
    db: AsyncSession,
    *,
    department_id: int | None,
    level: str | None,
    distance_only: bool | None,
    is_active: bool | None,
    q: str | None,
    page: int,
    page_size: int,
) -> tuple[list[Specialty], int]:
    stmt = select(Specialty)
    if department_id is not None:
        stmt = stmt.where(Specialty.department_id == department_id)
    if level is not None:
        stmt = stmt.where(Specialty.level == level)
    if distance_only is True:
        stmt = stmt.where(Specialty.distance_enabled.is_(True))
    if is_active is not None:
        stmt = stmt.where(Specialty.is_active.is_(is_active))
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Specialty.code).like(like),
                func.lower(Specialty.name).like(like),
            )
        )
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.order_by(Specialty.id).offset((page - 1) * page_size).limit(page_size)
    items = list((await db.execute(stmt)).scalars().all())
    return items, int(total)


async def get_specialty(db: AsyncSession, sp_id: int) -> Specialty:
    sp = await db.get(Specialty, sp_id)
    if sp is None:
        raise NotFoundError("Yo'nalish topilmadi")
    return sp


async def create_specialty(db: AsyncSession, data: SpecialtyCreateRequest) -> Specialty:
    if (await db.get(Department, data.department_id)) is None:
        raise NotFoundError("Tanlangan kafedra topilmadi")
    dup = await db.execute(select(Specialty).where(Specialty.code == data.code))
    if dup.scalar_one_or_none():
        raise ConflictError(f"Yo'nalish '{data.code}' kodi bilan mavjud")
    sp = Specialty(**data.model_dump())
    db.add(sp)
    await db.flush()
    return sp


async def update_specialty(
    db: AsyncSession, sp_id: int, data: SpecialtyUpdateRequest
) -> Specialty:
    sp = await get_specialty(db, sp_id)

    # 559-qaror 15-band — level + quota cross check
    new_level = data.level if data.level is not None else sp.level
    new_quota = data.annual_quota if data.annual_quota is not None else sp.annual_quota
    if new_quota is not None:
        if new_level == "bachelor" and new_quota > 300:
            raise ConflictError(
                "Bakalavr yo'nalishi uchun annual_quota maksimal 300"
            )
        if new_level == "master" and new_quota > 30:
            raise ConflictError(
                "Magistr yo'nalishi uchun annual_quota maksimal 30"
            )

    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(sp, k, v)
    await db.flush()
    return sp


async def delete_specialty(db: AsyncSession, sp_id: int) -> None:
    sp = await get_specialty(db, sp_id)
    await db.delete(sp)
    await db.flush()


async def enable_distance(db: AsyncSession, sp_id: int) -> Specialty:
    """559-qaror 14-band — masofaviy ta'limga ruxsat berish."""
    sp = await get_specialty(db, sp_id)
    sp.distance_enabled = True
    await db.flush()
    return sp


# ============================================================================
# Subject
# ============================================================================


async def list_subjects(
    db: AsyncSession,
    *,
    department_id: int | None,
    language: str | None,
    is_active: bool | None,
    q: str | None,
    page: int,
    page_size: int,
) -> tuple[list[Subject], int]:
    stmt = select(Subject)
    if department_id is not None:
        stmt = stmt.where(Subject.department_id == department_id)
    if language is not None:
        stmt = stmt.where(Subject.language == language)
    if is_active is not None:
        stmt = stmt.where(Subject.is_active.is_(is_active))
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(func.lower(Subject.code).like(like), func.lower(Subject.name).like(like))
        )
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = (
        stmt.options(selectinload(Subject.prerequisites))
        .order_by(Subject.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().unique().all())
    return items, int(total)


async def get_subject(db: AsyncSession, sub_id: int) -> Subject:
    stmt = select(Subject).where(Subject.id == sub_id).options(selectinload(Subject.prerequisites))
    s = (await db.execute(stmt)).scalar_one_or_none()
    if s is None:
        raise NotFoundError("Fan topilmadi")
    return s


async def _set_subject_prerequisites(
    db: AsyncSession, subject_id: int, prerequisite_ids: list[int]
) -> None:
    """Pre-rekvizitlarni replace qiladi."""
    # Eski linklarni o'chirish
    existing = await db.execute(
        select(SubjectPrerequisite).where(SubjectPrerequisite.subject_id == subject_id)
    )
    for pr in existing.scalars().all():
        await db.delete(pr)

    # Yangilarini qo'shish (self-reference oldini olamiz)
    for pid in prerequisite_ids:
        if pid == subject_id:
            continue
        db.add(SubjectPrerequisite(subject_id=subject_id, prerequisite_id=pid))


async def create_subject(db: AsyncSession, data: SubjectCreateRequest) -> Subject:
    if (await db.get(Department, data.department_id)) is None:
        raise NotFoundError("Tanlangan kafedra topilmadi")
    dup = await db.execute(select(Subject).where(Subject.code == data.code))
    if dup.scalar_one_or_none():
        raise ConflictError(f"Fan '{data.code}' kodi bilan mavjud")

    payload = data.model_dump(exclude={"prerequisite_ids"})
    s = Subject(**payload)
    db.add(s)
    await db.flush()

    if data.prerequisite_ids:
        await _set_subject_prerequisites(db, s.id, data.prerequisite_ids)
        await db.flush()
    return await get_subject(db, s.id)


async def update_subject(
    db: AsyncSession, sub_id: int, data: SubjectUpdateRequest
) -> Subject:
    s = await get_subject(db, sub_id)
    payload = data.model_dump(exclude_unset=True, exclude={"prerequisite_ids"})
    for k, v in payload.items():
        setattr(s, k, v)
    if data.prerequisite_ids is not None:
        await _set_subject_prerequisites(db, sub_id, data.prerequisite_ids)
    await db.flush()
    return await get_subject(db, sub_id)


async def delete_subject(db: AsyncSession, sub_id: int) -> None:
    s = await get_subject(db, sub_id)
    await db.delete(s)
    await db.flush()


# ============================================================================
# Curriculum
# ============================================================================


async def list_curricula(
    db: AsyncSession,
    *,
    specialty_id: int | None,
    is_active: bool | None,
    page: int,
    page_size: int,
) -> tuple[list[Curriculum], int]:
    stmt = select(Curriculum)
    if specialty_id is not None:
        stmt = stmt.where(Curriculum.specialty_id == specialty_id)
    if is_active is not None:
        stmt = stmt.where(Curriculum.is_active.is_(is_active))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = (
        stmt.options(selectinload(Curriculum.curriculum_subjects))
        .order_by(desc(Curriculum.id))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().unique().all())
    return items, int(total)


async def get_curriculum(db: AsyncSession, curr_id: int) -> Curriculum:
    stmt = (
        select(Curriculum)
        .where(Curriculum.id == curr_id)
        .options(selectinload(Curriculum.curriculum_subjects))
    )
    c = (await db.execute(stmt)).scalar_one_or_none()
    if c is None:
        raise NotFoundError("O'quv reja topilmadi")
    return c


async def create_curriculum(db: AsyncSession, data: CurriculumCreateRequest) -> Curriculum:
    if (await db.get(Specialty, data.specialty_id)) is None:
        raise NotFoundError("Tanlangan yo'nalish topilmadi")

    payload = data.model_dump(exclude={"subjects"})
    c = Curriculum(**payload)
    db.add(c)
    await db.flush()

    for s in data.subjects:
        if (await db.get(Subject, s.subject_id)) is None:
            raise NotFoundError(f"Fan id={s.subject_id} topilmadi")
        db.add(
            CurriculumSubject(
                curriculum_id=c.id,
                subject_id=s.subject_id,
                semester=s.semester,
                is_required=s.is_required,
            )
        )
    await db.flush()
    return await get_curriculum(db, c.id)


async def update_curriculum(
    db: AsyncSession, curr_id: int, data: CurriculumUpdateRequest
) -> Curriculum:
    c = await get_curriculum(db, curr_id)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    await db.flush()
    return await get_curriculum(db, curr_id)


async def delete_curriculum(db: AsyncSession, curr_id: int) -> None:
    c = await get_curriculum(db, curr_id)
    await db.delete(c)
    await db.flush()


async def clone_curriculum(
    db: AsyncSession, curr_id: int, *, new_version: str, new_valid_from: date
) -> Curriculum:
    """Yangi versiya — fanlar bilan birga nusxa olinadi."""
    src = await get_curriculum(db, curr_id)
    new_c = Curriculum(
        specialty_id=src.specialty_id,
        name=src.name,
        version=new_version,
        valid_from=new_valid_from,
        based_on=src.based_on,
        standard_code=src.standard_code,
        total_credits=src.total_credits,
        is_active=True,
    )
    db.add(new_c)
    await db.flush()

    for cs in src.curriculum_subjects:
        db.add(
            CurriculumSubject(
                curriculum_id=new_c.id,
                subject_id=cs.subject_id,
                semester=cs.semester,
                is_required=cs.is_required,
            )
        )
    await db.flush()
    return await get_curriculum(db, new_c.id)


async def approve_curriculum(
    db: AsyncSession, curr_id: int, *, approver_id: int
) -> Curriculum:
    c = await get_curriculum(db, curr_id)
    c.approved_by = approver_id
    c.approved_at = _now()
    await db.flush()
    return c


# ============================================================================
# Academic calendar
# ============================================================================


async def list_calendars(
    db: AsyncSession, *, organization_id: int | None, is_active: bool | None
) -> list[AcademicCalendar]:
    stmt = select(AcademicCalendar).order_by(desc(AcademicCalendar.academic_year))
    if organization_id is not None:
        stmt = stmt.where(AcademicCalendar.organization_id == organization_id)
    if is_active is not None:
        stmt = stmt.where(AcademicCalendar.is_active.is_(is_active))
    return list((await db.execute(stmt)).scalars().all())


async def get_calendar(db: AsyncSession, cal_id: int) -> AcademicCalendar:
    c = await db.get(AcademicCalendar, cal_id)
    if c is None:
        raise NotFoundError("Akademik kalendar topilmadi")
    return c


async def get_current_calendar(
    db: AsyncSession, organization_id: int
) -> AcademicCalendar | None:
    today = date.today()
    stmt = (
        select(AcademicCalendar)
        .where(
            AcademicCalendar.organization_id == organization_id,
            AcademicCalendar.is_active.is_(True),
            AcademicCalendar.start_date <= today,
            AcademicCalendar.end_date >= today,
        )
        .order_by(desc(AcademicCalendar.start_date))
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def create_calendar(
    db: AsyncSession, data: AcademicCalendarCreateRequest
) -> AcademicCalendar:
    from app.core.tenant import get_xiu_org_id

    payload = data.model_dump()
    if payload.get("organization_id") is None:
        payload["organization_id"] = await get_xiu_org_id(db)

    if (await db.get(Organization, payload["organization_id"])) is None:
        raise NotFoundError("Universitet topilmadi")
    dup = await db.execute(
        select(AcademicCalendar).where(
            AcademicCalendar.organization_id == payload["organization_id"],
            AcademicCalendar.academic_year == data.academic_year,
        )
    )
    if dup.scalar_one_or_none():
        raise ConflictError(f"{data.academic_year} kalendar mavjud")

    payload["semesters"] = [s if isinstance(s, dict) else s.model_dump(mode="json") for s in data.semesters]
    payload["holidays"] = [h if isinstance(h, dict) else h.model_dump(mode="json") for h in data.holidays]

    c = AcademicCalendar(**payload)
    db.add(c)
    await db.flush()
    return c


async def update_calendar(
    db: AsyncSession, cal_id: int, data: AcademicCalendarUpdateRequest
) -> AcademicCalendar:
    c = await get_calendar(db, cal_id)
    payload = data.model_dump(exclude_unset=True)
    if "semesters" in payload and payload["semesters"] is not None:
        payload["semesters"] = [
            s if isinstance(s, dict) else s.model_dump(mode="json") for s in data.semesters or []
        ]
    if "holidays" in payload and payload["holidays"] is not None:
        payload["holidays"] = [
            h if isinstance(h, dict) else h.model_dump(mode="json") for h in data.holidays or []
        ]
    for k, v in payload.items():
        setattr(c, k, v)
    await db.flush()
    return c


async def delete_calendar(db: AsyncSession, cal_id: int) -> None:
    c = await get_calendar(db, cal_id)
    await db.delete(c)
    await db.flush()

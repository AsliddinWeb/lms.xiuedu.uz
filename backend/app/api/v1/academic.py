"""Academic CRUD endpoints — Phase 2a.

Spec: docs/03-modules/03-academic.md
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.cache_headers import cache_private
from app.modules.academic import service
from app.modules.academic.models import Subject
from app.modules.academic.schemas import (
    AcademicCalendarCreateRequest,
    AcademicCalendarPublic,
    AcademicCalendarUpdateRequest,
    CurriculumCloneRequest,
    CurriculumCreateRequest,
    CurriculumPublic,
    CurriculumSubjectPublic,
    CurriculumUpdateRequest,
    DepartmentCreateRequest,
    DepartmentPublic,
    DepartmentUpdateRequest,
    FacultyCreateRequest,
    FacultyPublic,
    FacultyUpdateRequest,
    OrgCreateRequest,
    OrgPublic,
    OrgUpdateRequest,
    PaginatedCurricula,
    PaginatedDepartments,
    PaginatedFaculties,
    PaginatedSpecialties,
    PaginatedSubjects,
    SpecialtyCreateRequest,
    SpecialtyPublic,
    SpecialtyUpdateRequest,
    SubjectCreateRequest,
    SubjectPublic,
    SubjectUpdateRequest,
)
from app.modules.auth.dependencies import (
    CurrentUser,
    DbSession,
    require_permission,
)
from app.modules.users.models import User

router = APIRouter()


def _subject_to_public(s: Subject) -> SubjectPublic:
    return SubjectPublic(
        id=s.id,
        department_id=s.department_id,
        code=s.code,
        name=s.name,
        short_name=s.short_name,
        description=s.description,
        credits=s.credits,
        lecture_hours=s.lecture_hours,
        practice_hours=s.practice_hours,
        seminar_hours=s.seminar_hours,
        self_study_hours=s.self_study_hours,
        language=s.language,
        prerequisite_ids=[p.id for p in s.prerequisites],
        is_active=s.is_active,
        created_at=s.created_at,
    )


# ============================================================================
# Organizations (super admin)
# ============================================================================


@router.get("/organizations", response_model=list[OrgPublic])
async def list_orgs(
    db: DbSession,
    _u: User = Depends(require_permission("org.read")),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> list[OrgPublic]:
    items, _total = await service.list_organizations(db, q=q, page=page, page_size=page_size)
    return [OrgPublic.model_validate(o) for o in items]


@router.get("/organizations/{org_id}", response_model=OrgPublic)
async def get_org(
    org_id: int, db: DbSession, _u: User = Depends(require_permission("org.read"))
) -> OrgPublic:
    return OrgPublic.model_validate(await service.get_organization(db, org_id))


@router.post(
    "/organizations",
    response_model=OrgPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_org(
    data: OrgCreateRequest,
    db: DbSession,
    _u: User = Depends(require_permission("platform.*")),
) -> OrgPublic:
    org = await service.create_organization(db, data.model_dump())
    await db.commit()
    return OrgPublic.model_validate(org)


@router.patch("/organizations/{org_id}", response_model=OrgPublic)
async def update_org(
    org_id: int,
    data: OrgUpdateRequest,
    db: DbSession,
    _u: User = Depends(require_permission("org.manage")),
) -> OrgPublic:
    org = await service.update_organization(db, org_id, data.model_dump(exclude_unset=True))
    await db.commit()
    return OrgPublic.model_validate(org)


# ============================================================================
# Faculties
# ============================================================================


@router.get("/faculties", response_model=PaginatedFaculties)
async def list_faculties(
    response: Response,
    db: DbSession,
    _u: User = Depends(require_permission("faculty.read")),
    organization_id: int | None = Query(None),
    is_active: bool | None = Query(None),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedFaculties:
    items, total = await service.list_faculties(
        db,
        organization_id=organization_id,
        is_active=is_active,
        q=q,
        page=page,
        page_size=page_size,
    )
    cache_private(response, seconds=60)
    return PaginatedFaculties(
        items=[FacultyPublic.model_validate(f) for f in items], total=total
    )


@router.get("/faculties/{faculty_id}", response_model=FacultyPublic)
async def get_faculty(
    faculty_id: int, db: DbSession, _u: User = Depends(require_permission("faculty.read"))
) -> FacultyPublic:
    return FacultyPublic.model_validate(await service.get_faculty(db, faculty_id))


@router.post("/faculties", response_model=FacultyPublic, status_code=status.HTTP_201_CREATED)
async def create_faculty(
    data: FacultyCreateRequest,
    db: DbSession,
    _u: User = Depends(require_permission("faculty.manage")),
) -> FacultyPublic:
    f = await service.create_faculty(db, data)
    await db.commit()
    return FacultyPublic.model_validate(f)


@router.patch("/faculties/{faculty_id}", response_model=FacultyPublic)
async def update_faculty(
    faculty_id: int,
    data: FacultyUpdateRequest,
    db: DbSession,
    _u: User = Depends(require_permission("faculty.manage")),
) -> FacultyPublic:
    f = await service.update_faculty(db, faculty_id, data)
    await db.commit()
    return FacultyPublic.model_validate(f)


@router.delete("/faculties/{faculty_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_faculty(
    faculty_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("faculty.manage")),
) -> Response:
    await service.delete_faculty(db, faculty_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Departments
# ============================================================================


@router.get("/departments", response_model=PaginatedDepartments)
async def list_departments(
    response: Response,
    db: DbSession,
    _u: User = Depends(require_permission("department.read")),
    faculty_id: int | None = Query(None),
    organization_id: int | None = Query(None),
    is_active: bool | None = Query(None),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedDepartments:
    items, total = await service.list_departments(
        db,
        faculty_id=faculty_id,
        organization_id=organization_id,
        is_active=is_active,
        q=q,
        page=page,
        page_size=page_size,
    )
    cache_private(response, seconds=60)
    return PaginatedDepartments(
        items=[DepartmentPublic.model_validate(d) for d in items], total=total
    )


@router.get("/departments/{dep_id}", response_model=DepartmentPublic)
async def get_department(
    dep_id: int, db: DbSession, _u: User = Depends(require_permission("department.read"))
) -> DepartmentPublic:
    return DepartmentPublic.model_validate(await service.get_department(db, dep_id))


@router.post(
    "/departments", response_model=DepartmentPublic, status_code=status.HTTP_201_CREATED
)
async def create_department(
    data: DepartmentCreateRequest,
    db: DbSession,
    _u: User = Depends(require_permission("department.manage")),
) -> DepartmentPublic:
    d = await service.create_department(db, data)
    await db.commit()
    return DepartmentPublic.model_validate(d)


@router.patch("/departments/{dep_id}", response_model=DepartmentPublic)
async def update_department(
    dep_id: int,
    data: DepartmentUpdateRequest,
    db: DbSession,
    _u: User = Depends(require_permission("department.manage")),
) -> DepartmentPublic:
    d = await service.update_department(db, dep_id, data)
    await db.commit()
    return DepartmentPublic.model_validate(d)


@router.delete("/departments/{dep_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    dep_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("department.manage")),
) -> Response:
    await service.delete_department(db, dep_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Specialties (559-qaror 14, 15-bandlar)
# ============================================================================


@router.get("/specialties", response_model=PaginatedSpecialties)
async def list_specialties(
    response: Response,
    db: DbSession,
    _u: User = Depends(require_permission("specialty.read")),
    department_id: int | None = Query(None),
    level: str | None = Query(None, description="bachelor | master | phd"),
    distance_only: bool | None = Query(None),
    is_active: bool | None = Query(None),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedSpecialties:
    items, total = await service.list_specialties(
        db,
        department_id=department_id,
        level=level,
        distance_only=distance_only,
        is_active=is_active,
        q=q,
        page=page,
        page_size=page_size,
    )
    cache_private(response, seconds=60)
    return PaginatedSpecialties(
        items=[SpecialtyPublic.model_validate(s) for s in items], total=total
    )


@router.get("/specialties/{sp_id}", response_model=SpecialtyPublic)
async def get_specialty(
    sp_id: int, db: DbSession, _u: User = Depends(require_permission("specialty.read"))
) -> SpecialtyPublic:
    return SpecialtyPublic.model_validate(await service.get_specialty(db, sp_id))


@router.post(
    "/specialties", response_model=SpecialtyPublic, status_code=status.HTTP_201_CREATED
)
async def create_specialty(
    data: SpecialtyCreateRequest,
    db: DbSession,
    _u: User = Depends(require_permission("specialty.manage")),
) -> SpecialtyPublic:
    sp = await service.create_specialty(db, data)
    await db.commit()
    return SpecialtyPublic.model_validate(sp)


@router.patch("/specialties/{sp_id}", response_model=SpecialtyPublic)
async def update_specialty(
    sp_id: int,
    data: SpecialtyUpdateRequest,
    db: DbSession,
    _u: User = Depends(require_permission("specialty.manage")),
) -> SpecialtyPublic:
    sp = await service.update_specialty(db, sp_id, data)
    await db.commit()
    return SpecialtyPublic.model_validate(sp)


@router.delete("/specialties/{sp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_specialty(
    sp_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("specialty.manage")),
) -> Response:
    await service.delete_specialty(db, sp_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/specialties/{sp_id}/enable-distance",
    response_model=SpecialtyPublic,
    summary="Masofaviy ta'limga ruxsat berish",
)
async def enable_distance(
    sp_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("specialty.manage")),
) -> SpecialtyPublic:
    sp = await service.enable_distance(db, sp_id)
    await db.commit()
    return SpecialtyPublic.model_validate(sp)


# ============================================================================
# Subjects
# ============================================================================


@router.get("/subjects", response_model=PaginatedSubjects)
async def list_subjects(
    response: Response,
    db: DbSession,
    _u: User = Depends(require_permission("subject.read")),
    department_id: int | None = Query(None),
    language: str | None = Query(None),
    is_active: bool | None = Query(None),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedSubjects:
    items, total = await service.list_subjects(
        db,
        department_id=department_id,
        language=language,
        is_active=is_active,
        q=q,
        page=page,
        page_size=page_size,
    )
    cache_private(response, seconds=60)
    return PaginatedSubjects(
        items=[_subject_to_public(s) for s in items], total=total
    )


@router.get("/subjects/{sub_id}", response_model=SubjectPublic)
async def get_subject(
    sub_id: int, db: DbSession, _u: User = Depends(require_permission("subject.read"))
) -> SubjectPublic:
    return _subject_to_public(await service.get_subject(db, sub_id))


@router.post("/subjects", response_model=SubjectPublic, status_code=status.HTTP_201_CREATED)
async def create_subject(
    data: SubjectCreateRequest,
    db: DbSession,
    _u: User = Depends(require_permission("subject.manage")),
) -> SubjectPublic:
    s = await service.create_subject(db, data)
    await db.commit()
    return _subject_to_public(s)


@router.patch("/subjects/{sub_id}", response_model=SubjectPublic)
async def update_subject(
    sub_id: int,
    data: SubjectUpdateRequest,
    db: DbSession,
    _u: User = Depends(require_permission("subject.manage")),
) -> SubjectPublic:
    s = await service.update_subject(db, sub_id, data)
    await db.commit()
    return _subject_to_public(s)


@router.delete("/subjects/{sub_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subject(
    sub_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("subject.manage")),
) -> Response:
    await service.delete_subject(db, sub_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Curricula
# ============================================================================


def _curriculum_to_public(c) -> CurriculumPublic:  # noqa: ANN001
    return CurriculumPublic(
        id=c.id,
        specialty_id=c.specialty_id,
        name=c.name,
        version=c.version,
        valid_from=c.valid_from,
        valid_until=c.valid_until,
        based_on=c.based_on,
        standard_code=c.standard_code,
        total_credits=c.total_credits,
        is_active=c.is_active,
        approved_by=c.approved_by,
        approved_at=c.approved_at,
        created_at=c.created_at,
        subjects=[CurriculumSubjectPublic.model_validate(s) for s in c.curriculum_subjects],
    )


@router.get("/curricula", response_model=PaginatedCurricula)
async def list_curricula(
    db: DbSession,
    _u: User = Depends(require_permission("curriculum.read")),
    specialty_id: int | None = Query(None),
    is_active: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedCurricula:
    items, total = await service.list_curricula(
        db, specialty_id=specialty_id, is_active=is_active, page=page, page_size=page_size
    )
    return PaginatedCurricula(items=[_curriculum_to_public(c) for c in items], total=total)


@router.get("/curricula/{curr_id}", response_model=CurriculumPublic)
async def get_curriculum(
    curr_id: int, db: DbSession, _u: User = Depends(require_permission("curriculum.read"))
) -> CurriculumPublic:
    return _curriculum_to_public(await service.get_curriculum(db, curr_id))


@router.post(
    "/curricula", response_model=CurriculumPublic, status_code=status.HTTP_201_CREATED
)
async def create_curriculum(
    data: CurriculumCreateRequest,
    db: DbSession,
    _u: User = Depends(require_permission("curriculum.manage")),
) -> CurriculumPublic:
    c = await service.create_curriculum(db, data)
    await db.commit()
    return _curriculum_to_public(c)


@router.patch("/curricula/{curr_id}", response_model=CurriculumPublic)
async def update_curriculum(
    curr_id: int,
    data: CurriculumUpdateRequest,
    db: DbSession,
    _u: User = Depends(require_permission("curriculum.manage")),
) -> CurriculumPublic:
    c = await service.update_curriculum(db, curr_id, data)
    await db.commit()
    return _curriculum_to_public(c)


@router.delete("/curricula/{curr_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_curriculum(
    curr_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("curriculum.manage")),
) -> Response:
    await service.delete_curriculum(db, curr_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/curricula/{curr_id}/clone",
    response_model=CurriculumPublic,
    summary="Yangi versiya — fanlar bilan birga nusxa olish",
)
async def clone_curriculum(
    curr_id: int,
    data: CurriculumCloneRequest,
    db: DbSession,
    _u: User = Depends(require_permission("curriculum.manage")),
) -> CurriculumPublic:
    c = await service.clone_curriculum(
        db, curr_id, new_version=data.new_version, new_valid_from=data.new_valid_from
    )
    await db.commit()
    return _curriculum_to_public(c)


@router.post("/curricula/{curr_id}/approve", response_model=CurriculumPublic)
async def approve_curriculum(
    curr_id: int,
    db: DbSession,
    actor: CurrentUser,
    _u: User = Depends(require_permission("curriculum.manage")),
) -> CurriculumPublic:
    c = await service.approve_curriculum(db, curr_id, approver_id=actor.id)
    await db.commit()
    return _curriculum_to_public(c)


# ============================================================================
# Academic calendars
# ============================================================================


@router.get("/academic-calendars", response_model=list[AcademicCalendarPublic])
async def list_calendars(
    db: DbSession,
    _u: User = Depends(require_permission("calendar.read")),
    organization_id: int | None = Query(None),
    is_active: bool | None = Query(None),
) -> list[AcademicCalendarPublic]:
    items = await service.list_calendars(
        db, organization_id=organization_id, is_active=is_active
    )
    return [AcademicCalendarPublic.model_validate(c) for c in items]


@router.get("/academic-calendars/current", response_model=AcademicCalendarPublic | None)
async def get_current_calendar(
    db: DbSession,
    _u: User = Depends(require_permission("calendar.read")),
    organization_id: int = Query(...),
) -> AcademicCalendarPublic | None:
    c = await service.get_current_calendar(db, organization_id)
    return AcademicCalendarPublic.model_validate(c) if c else None


@router.get("/academic-calendars/{cal_id}", response_model=AcademicCalendarPublic)
async def get_calendar(
    cal_id: int, db: DbSession, _u: User = Depends(require_permission("calendar.read"))
) -> AcademicCalendarPublic:
    return AcademicCalendarPublic.model_validate(await service.get_calendar(db, cal_id))


@router.post(
    "/academic-calendars",
    response_model=AcademicCalendarPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_calendar(
    data: AcademicCalendarCreateRequest,
    db: DbSession,
    _u: User = Depends(require_permission("calendar.manage")),
) -> AcademicCalendarPublic:
    c = await service.create_calendar(db, data)
    await db.commit()
    return AcademicCalendarPublic.model_validate(c)


@router.patch("/academic-calendars/{cal_id}", response_model=AcademicCalendarPublic)
async def update_calendar(
    cal_id: int,
    data: AcademicCalendarUpdateRequest,
    db: DbSession,
    _u: User = Depends(require_permission("calendar.manage")),
) -> AcademicCalendarPublic:
    c = await service.update_calendar(db, cal_id, data)
    await db.commit()
    return AcademicCalendarPublic.model_validate(c)


@router.delete("/academic-calendars/{cal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_calendar(
    cal_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("calendar.manage")),
) -> Response:
    await service.delete_calendar(db, cal_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

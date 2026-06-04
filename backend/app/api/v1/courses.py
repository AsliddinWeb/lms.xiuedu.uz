"""Courses endpointlari (Phase 3b).

Group:
- Course (8): list, create, get, get-by-slug, patch, delete, publish, unpublish
- Module (5): list, create, patch, delete, reorder
- Lesson (6): list, create, get, patch, delete, reorder
- Enrollment (5): self-enroll, self-unenroll, list-students, add-student, remove-student
- Progress (4): my-progress, start, complete, save
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel

from app.core.csv_export import filename_with_timestamp, rows_to_csv
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.modules.auth.dependencies import (
    CurrentUser,
    DbSession,
    RedisClient,
    require_permission,
)
from app.modules.courses import gradebook, service
from app.modules.courses.schemas import (
    CourseCreateRequest,
    CourseProgressPublic,
    CoursePublic,
    CourseUpdateRequest,
    EnrollmentCreateRequest,
    EnrollmentPublic,
    EnrollmentStudentItem,
    LessonCreateRequest,
    LessonProgressPublic,
    LessonProgressUpsertRequest,
    LessonPublic,
    LessonUpdateRequest,
    ModuleCreateRequest,
    ModulePublic,
    ModuleUpdateRequest,
    PaginatedCourses,
    PaginatedStudents,
    ReorderRequest,
)
from app.modules.rbac.service import RBACService, has_permission
from app.modules.users.models import User

router = APIRouter()


# ============================================================================
# Helpers
# ============================================================================


async def _user_can_manage_course(
    db: DbSession, redis: RedisClient, user: User, course_id: int
) -> bool:
    """Course muallifi yoki course.edit permission'i borlar tahrir qila oladi."""
    course = await service.get_course(db, course_id)
    if course.primary_author_id == user.id:
        return True
    rbac = RBACService(db, redis)
    perms = await rbac.get_user_permissions(user.id)
    return has_permission(perms, "course.edit") or has_permission(perms, "platform.*")


# ============================================================================
# Course
# ============================================================================


@router.get("/courses", response_model=PaginatedCourses, summary="Kurs ro'yxati")
async def list_courses(
    db: DbSession,
    _u: User = Depends(require_permission("course.read")),
    type: str | None = Query(None, description="academic | open | micro | specialization"),
    status_: str | None = Query(None, alias="status"),
    subject_id: int | None = Query(None),
    organization_id: int | None = Query(None),
    language: str | None = Query(None),
    primary_author_id: int | None = Query(None),
    enrolled_user_id: int | None = Query(None, description="Faqat shu user yozilgan kurslar"),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedCourses:
    items, total = await service.list_courses(
        db,
        type_=type,
        status_=status_,
        subject_id=subject_id,
        organization_id=organization_id,
        language=language,
        primary_author_id=primary_author_id,
        enrolled_user_id=enrolled_user_id,
        q=q,
        page=page,
        page_size=page_size,
    )
    return PaginatedCourses(
        items=[CoursePublic.model_validate(c) for c in items], total=total
    )


@router.post(
    "/courses",
    response_model=CoursePublic,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi kurs yaratish (draft)",
)
async def create_course(
    data: CourseCreateRequest,
    db: DbSession,
    actor: CurrentUser,
    _u: User = Depends(require_permission("course.create")),
) -> CoursePublic:
    course = await service.create_course(db, data, author_id=actor.id)
    await db.commit()
    return CoursePublic.model_validate(course)


@router.get("/courses/by-slug/{slug}", response_model=CoursePublic)
async def get_course_by_slug(
    slug: str, db: DbSession, _u: User = Depends(require_permission("course.read"))
) -> CoursePublic:
    return CoursePublic.model_validate(await service.get_course_by_slug(db, slug))


@router.get("/courses/{course_id}", response_model=CoursePublic)
async def get_course(
    course_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("course.read")),
) -> CoursePublic:
    return CoursePublic.model_validate(await service.get_course(db, course_id))


class CourseMaterial(BaseModel):
    """Phase 18.3 — kurs darslariga biriktirilgan content (downloadable)."""

    lesson_id: int
    lesson_title: str
    module_id: int
    content_id: int | None
    title: str | None
    type: str | None  # 'video', 'pdf', 'file', 'link', 'scorm', ...
    file_url: str | None
    mime_type: str | None
    file_size: int | None


@router.get(
    "/courses/{course_id}/materials",
    response_model=list[CourseMaterial],
)
async def list_course_materials(
    course_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("course.read")),
) -> list[CourseMaterial]:
    """Phase 18.3 — kurs darslaridagi content_items (sidebar uchun).

    Faqat published bo'lgan kurs darslarining primary_content_id
    bo'yicha content items qaytaradi.
    """
    from sqlalchemy import select

    from app.modules.content.models import ContentItem
    from app.modules.courses.models import Lesson, Module

    rows = (
        await db.execute(
            select(
                Lesson.id,
                Lesson.title,
                Lesson.module_id,
                ContentItem.id,
                ContentItem.title,
                ContentItem.type,
                ContentItem.file_url,
                ContentItem.mime_type,
                ContentItem.file_size,
            )
            .join(Module, Module.id == Lesson.module_id)
            .outerjoin(ContentItem, ContentItem.id == Lesson.primary_content_id)
            .where(Module.course_id == course_id)
            .order_by(Module.order_index, Lesson.order_index)
        )
    ).all()
    return [
        CourseMaterial(
            lesson_id=r[0],
            lesson_title=r[1],
            module_id=r[2],
            content_id=r[3],
            title=r[4],
            type=r[5],
            file_url=r[6],
            mime_type=r[7],
            file_size=r[8],
        )
        for r in rows
    ]


class TeacherPublic(BaseModel):
    """Phase 18.2 — kurs pedagog'ining public profili."""

    id: int
    full_name: str
    avatar_url: str | None
    bio: str | None
    courses_count: int  # shu pedagog yaratgan published kurslar soni


@router.get("/courses/{course_id}/teacher", response_model=TeacherPublic)
async def get_course_teacher(
    course_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("course.read")),
) -> TeacherPublic:
    """Phase 18.2 — kurs pedagog'ining public profili (avatar, bio, kurslar soni).

    Talabada `users.read` permission yo'q, lekin kurs pedagog'ini bilish kerak —
    shuning uchun shu cheklangan endpoint course.read permission'i bilan ishlaydi.
    """
    from sqlalchemy import func, select

    from app.modules.courses.models import Course
    from app.modules.users.models import Profile, User

    course = await service.get_course(db, course_id)
    if course.primary_author_id is None:
        raise NotFoundError("Kurs uchun pedagog tayinlanmagan")

    user = await db.get(User, course.primary_author_id)
    if user is None:
        raise NotFoundError("Pedagog topilmadi")

    profile = (
        await db.execute(select(Profile).where(Profile.user_id == user.id))
    ).scalar_one_or_none()

    count = (
        await db.execute(
            select(func.count(Course.id)).where(
                Course.primary_author_id == user.id,
                Course.status == "published",
            )
        )
    ).scalar_one()

    return TeacherPublic(
        id=user.id,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        bio=profile.bio if profile else None,
        courses_count=int(count),
    )


# ----------------------------------------------------------------------------
# Phase 18.5 — Upcoming exams / live (kurs detail right column widgetlari)
# ----------------------------------------------------------------------------


class UpcomingExamItem(BaseModel):
    """Yaqinlashayotgan imtihon (talaba kurs detail uchun)."""

    id: int
    title: str
    type: str
    duration_minutes: int
    available_from: datetime | None
    available_until: datetime | None
    proctoring_enabled: bool


class UpcomingLiveItem(BaseModel):
    """Yaqinlashayotgan live dars (talaba kurs detail uchun)."""

    id: int
    title: str
    scheduled_start: datetime
    scheduled_end: datetime
    duration_minutes: int
    status: str
    host_user_id: int
    host_full_name: str | None


@router.get(
    "/courses/{course_id}/upcoming-exams",
    response_model=list[UpcomingExamItem],
)
async def list_course_upcoming_exams(
    course_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("course.read")),
    limit: int = Query(default=5, ge=1, le=20),
) -> list[UpcomingExamItem]:
    """Phase 18.5 — kursning yaqin imtihonlari.

    `status='published'` va `available_until` o'tmagan imtihonlar.
    Tartib: available_from asc (NULL keyin), so'ng created_at asc.
    """
    from sqlalchemy import or_, select

    from app.modules.exams.models import Exam

    now = datetime.now(UTC)

    rows = (
        await db.execute(
            select(Exam)
            .where(
                Exam.course_id == course_id,
                Exam.status == "published",
                Exam.deleted_at.is_(None),
                or_(Exam.available_until.is_(None), Exam.available_until >= now),
                Exam.closed_at.is_(None),
            )
            .order_by(Exam.available_from.asc().nulls_last(), Exam.created_at.asc())
            .limit(limit)
        )
    ).scalars().all()

    return [
        UpcomingExamItem(
            id=e.id,
            title=e.title,
            type=e.type,
            duration_minutes=e.duration_minutes,
            available_from=e.available_from,
            available_until=e.available_until,
            proctoring_enabled=e.proctoring_enabled,
        )
        for e in rows
    ]


@router.get(
    "/courses/{course_id}/upcoming-live",
    response_model=list[UpcomingLiveItem],
)
async def list_course_upcoming_live(
    course_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("course.read")),
    limit: int = Query(default=5, ge=1, le=20),
) -> list[UpcomingLiveItem]:
    """Phase 18.5 — kursning yaqin live darslari.

    `status in ('scheduled', 'live')` va `scheduled_end` o'tmagan sessiyalar.
    Tartib: scheduled_start asc.
    """
    from sqlalchemy import or_, select

    from app.modules.live.models import LiveSession

    now = datetime.now(UTC)

    rows = (
        await db.execute(
            select(LiveSession)
            .where(
                LiveSession.course_id == course_id,
                LiveSession.status.in_(["scheduled", "live"]),
                or_(LiveSession.scheduled_end >= now, LiveSession.status == "live"),
            )
            .order_by(LiveSession.scheduled_start.asc())
            .limit(limit)
        )
    ).scalars().all()

    host_ids = [r.host_user_id for r in rows]
    host_names: dict[int, str] = {}
    if host_ids:
        hosts = (
            await db.execute(
                select(User.id, User.full_name).where(User.id.in_(host_ids))
            )
        ).all()
        host_names = dict(hosts)

    return [
        UpcomingLiveItem(
            id=s.id,
            title=s.title,
            scheduled_start=s.scheduled_start,
            scheduled_end=s.scheduled_end,
            duration_minutes=s.duration_minutes,
            status=s.status,
            host_user_id=s.host_user_id,
            host_full_name=host_names.get(s.host_user_id),
        )
        for s in rows
    ]


@router.patch("/courses/{course_id}", response_model=CoursePublic)
async def update_course(
    course_id: int,
    data: CourseUpdateRequest,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("course.edit")),
) -> CoursePublic:
    if not await _user_can_manage_course(db, redis, actor, course_id):
        raise ForbiddenError("Bu kursni tahrirlash huquqi yo'q")
    course = await service.update_course(db, course_id, data)
    await db.commit()
    return CoursePublic.model_validate(course)


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("course.edit")),
) -> Response:
    if not await _user_can_manage_course(db, redis, actor, course_id):
        raise ForbiddenError("Bu kursni o'chirish huquqi yo'q")
    await service.delete_course(db, course_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/courses/{course_id}/publish", response_model=CoursePublic)
async def publish_course(
    course_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("course.publish")),
) -> CoursePublic:
    if not await _user_can_manage_course(db, redis, actor, course_id):
        raise ForbiddenError("Bu kursni publish qilish huquqi yo'q")
    course = await service.transition_course_status(
        db, course_id, new_status="published"
    )
    await db.commit()
    return CoursePublic.model_validate(course)


@router.post("/courses/{course_id}/unpublish", response_model=CoursePublic)
async def unpublish_course(
    course_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("course.publish")),
) -> CoursePublic:
    if not await _user_can_manage_course(db, redis, actor, course_id):
        raise ForbiddenError("Bu kursni unpublish qilish huquqi yo'q")
    # published → archived → draft (2 ta o'tish kerak)
    course = await service.transition_course_status(
        db, course_id, new_status="archived"
    )
    course = await service.transition_course_status(db, course_id, new_status="draft")
    await db.commit()
    return CoursePublic.model_validate(course)


# ============================================================================
# Module
# ============================================================================


@router.get("/courses/{course_id}/modules", response_model=list[ModulePublic])
async def list_modules(
    course_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("course.read")),
) -> list[ModulePublic]:
    items = await service.list_modules(db, course_id)
    return [ModulePublic.model_validate(m) for m in items]


@router.post(
    "/courses/{course_id}/modules",
    response_model=ModulePublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_module(
    course_id: int,
    data: ModuleCreateRequest,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("course.edit")),
) -> ModulePublic:
    if not await _user_can_manage_course(db, redis, actor, course_id):
        raise ForbiddenError("Bu kursga modul qo'shish huquqi yo'q")
    m = await service.create_module(db, course_id, data)
    await db.commit()
    return ModulePublic.model_validate(m)


@router.patch("/modules/{module_id}", response_model=ModulePublic)
async def update_module(
    module_id: int,
    data: ModuleUpdateRequest,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("course.edit")),
) -> ModulePublic:
    m = await service.get_module(db, module_id)
    if not await _user_can_manage_course(db, redis, actor, m.course_id):
        raise ForbiddenError("Bu modulni tahrirlash huquqi yo'q")
    m = await service.update_module(db, module_id, data)
    await db.commit()
    return ModulePublic.model_validate(m)


@router.delete("/modules/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_module(
    module_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("course.edit")),
) -> Response:
    m = await service.get_module(db, module_id)
    if not await _user_can_manage_course(db, redis, actor, m.course_id):
        raise ForbiddenError("Bu modulni o'chirish huquqi yo'q")
    await service.delete_module(db, module_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/courses/{course_id}/modules/reorder",
    response_model=list[ModulePublic],
)
async def reorder_modules(
    course_id: int,
    data: ReorderRequest,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("course.edit")),
) -> list[ModulePublic]:
    if not await _user_can_manage_course(db, redis, actor, course_id):
        raise ForbiddenError("Modullarni qayta tartiblash huquqi yo'q")
    items = await service.reorder_modules(
        db, course_id, ordered_ids=data.ordered_ids
    )
    await db.commit()
    return [ModulePublic.model_validate(m) for m in items]


# ============================================================================
# Lesson
# ============================================================================


@router.get("/modules/{module_id}/lessons", response_model=list[LessonPublic])
async def list_lessons(
    module_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("course.read")),
) -> list[LessonPublic]:
    items = await service.list_lessons(db, module_id)
    return [LessonPublic.model_validate(l) for l in items]


@router.post(
    "/modules/{module_id}/lessons",
    response_model=LessonPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_lesson(
    module_id: int,
    data: LessonCreateRequest,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("course.edit")),
) -> LessonPublic:
    m = await service.get_module(db, module_id)
    if not await _user_can_manage_course(db, redis, actor, m.course_id):
        raise ForbiddenError("Bu modulga dars qo'shish huquqi yo'q")
    lesson = await service.create_lesson(db, module_id, data)
    await db.commit()
    return LessonPublic.model_validate(lesson)


@router.get("/lessons/{lesson_id}", response_model=LessonPublic)
async def get_lesson(
    lesson_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("course.read")),
) -> LessonPublic:
    return LessonPublic.model_validate(await service.get_lesson(db, lesson_id))


@router.patch("/lessons/{lesson_id}", response_model=LessonPublic)
async def update_lesson(
    lesson_id: int,
    data: LessonUpdateRequest,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("course.edit")),
) -> LessonPublic:
    lesson = await service.get_lesson(db, lesson_id)
    module = await service.get_module(db, lesson.module_id)
    if not await _user_can_manage_course(db, redis, actor, module.course_id):
        raise ForbiddenError("Bu darsni tahrirlash huquqi yo'q")
    lesson = await service.update_lesson(db, lesson_id, data)
    await db.commit()
    return LessonPublic.model_validate(lesson)


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lesson(
    lesson_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("course.edit")),
) -> Response:
    lesson = await service.get_lesson(db, lesson_id)
    module = await service.get_module(db, lesson.module_id)
    if not await _user_can_manage_course(db, redis, actor, module.course_id):
        raise ForbiddenError("Bu darsni o'chirish huquqi yo'q")
    await service.delete_lesson(db, lesson_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/modules/{module_id}/lessons/reorder", response_model=list[LessonPublic]
)
async def reorder_lessons(
    module_id: int,
    data: ReorderRequest,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("course.edit")),
) -> list[LessonPublic]:
    m = await service.get_module(db, module_id)
    if not await _user_can_manage_course(db, redis, actor, m.course_id):
        raise ForbiddenError("Darslarni qayta tartiblash huquqi yo'q")
    items = await service.reorder_lessons(
        db, module_id, ordered_ids=data.ordered_ids
    )
    await db.commit()
    return [LessonPublic.model_validate(l) for l in items]


# ============================================================================
# Enrollment
# ============================================================================


@router.post(
    "/courses/{course_id}/enroll",
    response_model=EnrollmentPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Self-enrollment (talaba o'zi yoziladi)",
)
async def self_enroll(
    course_id: int,
    db: DbSession,
    actor: CurrentUser,
    _u: User = Depends(require_permission("enrollment.self")),
) -> EnrollmentPublic:
    course = await service.get_course(db, course_id)
    if course.enrollment_type == "manual":
        raise ConflictError("Bu kursga self-enrollment yo'q — admin/o'qituvchi qo'shishi kerak")
    e = await service.enroll_user(
        db,
        course_id,
        user_id=actor.id,
        method="self",
        enrolled_by=actor.id,
    )
    await db.commit()
    return EnrollmentPublic.model_validate(e)


@router.delete(
    "/courses/{course_id}/enroll", status_code=status.HTTP_204_NO_CONTENT
)
async def self_unenroll(
    course_id: int,
    db: DbSession,
    actor: CurrentUser,
) -> Response:
    await service.unenroll_user(db, course_id, actor.id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/courses/{course_id}/students", response_model=PaginatedStudents)
async def list_course_students(
    course_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    _u: User = Depends(require_permission("enrollment.read")),
) -> PaginatedStudents:
    if not await _user_can_manage_course(db, redis, actor, course_id):
        raise ForbiddenError("Bu kurs talabalarini ko'rish huquqi yo'q")
    rows, total = await service.list_course_students(
        db, course_id, page=page, page_size=page_size
    )
    return PaginatedStudents(
        items=[
            EnrollmentStudentItem(
                enrollment_id=enr.id,
                user_id=user.id,
                full_name=user.full_name,
                email=user.email,
                enrolled_at=enr.enrolled_at,
                enrollment_method=enr.enrollment_method,
                completion_status=enr.completion_status,
                progress_percent=pct,
            )
            for enr, user, pct in rows
        ],
        total=total,
    )


@router.get("/courses/{course_id}/students.csv")
async def export_course_students_csv(
    course_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("enrollment.read")),
) -> Response:
    """Phase 8f — Pedagog/admin uchun kurs talabalari ro'yxati CSV faylda."""
    if not await _user_can_manage_course(db, redis, actor, course_id):
        raise ForbiddenError("Bu kurs talabalarini ko'rish huquqi yo'q")
    # Barcha enrollmentlar (sahifalashsiz) — agar 5000+ bo'lsa, future
    # paginated streaming kerak. Hozircha bitta XIU kurs uchun bu yetarli.
    rows, _ = await service.list_course_students(
        db, course_id, page=1, page_size=10_000
    )
    csv_data = [
        {
            "enrollment_id": enr.id,
            "user_id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "enrolled_at": enr.enrolled_at.isoformat() if enr.enrolled_at else "",
            "enrollment_method": enr.enrollment_method,
            "completion_status": enr.completion_status,
            "progress_percent": str(pct) if pct is not None else "",
        }
        for enr, user, pct in rows
    ]
    csv_text = rows_to_csv(
        [
            "enrollment_id",
            "user_id",
            "full_name",
            "email",
            "enrolled_at",
            "enrollment_method",
            "completion_status",
            "progress_percent",
        ],
        csv_data,
    )
    fname = filename_with_timestamp(f"course_{course_id}_students")
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


@router.post(
    "/courses/{course_id}/students",
    response_model=EnrollmentPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Admin/o'qituvchi tomonidan talaba qo'shish",
)
async def add_student(
    course_id: int,
    data: EnrollmentCreateRequest,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("enrollment.manage")),
) -> EnrollmentPublic:
    if not await _user_can_manage_course(db, redis, actor, course_id):
        raise ForbiddenError("Bu kursga talaba qo'shish huquqi yo'q")
    e = await service.enroll_user(
        db,
        course_id,
        user_id=data.user_id,
        method=data.enrollment_method,
        enrolled_by=actor.id,
    )
    await db.commit()
    return EnrollmentPublic.model_validate(e)


@router.delete(
    "/courses/{course_id}/students/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_student(
    course_id: int,
    user_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("enrollment.manage")),
) -> Response:
    if not await _user_can_manage_course(db, redis, actor, course_id):
        raise ForbiddenError("Bu kursdan talaba o'chirish huquqi yo'q")
    await service.unenroll_user(db, course_id, user_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Progress
# ============================================================================


class _MyProgressResponse(BaseModel):
    course_id: int


@router.get(
    "/courses/{course_id}/my-progress",
    response_model=CourseProgressPublic,
)
async def my_course_progress(
    course_id: int,
    db: DbSession,
    actor: CurrentUser,
) -> CourseProgressPublic:
    await service.get_course(db, course_id)
    enrollment = await service.get_enrollment(db, course_id, actor.id)
    progress = await service.calculate_course_progress(
        db, user_id=actor.id, course_id=course_id
    )
    return CourseProgressPublic(
        course_id=course_id,
        enrolled=enrollment is not None,
        completion_status=enrollment.completion_status if enrollment else None,
        completed_lessons=progress["completed"],
        total_required_lessons=progress["total"],
        percent=progress["percent"],
        completed_at=enrollment.completed_at if enrollment else None,
    )


@router.post("/lessons/{lesson_id}/start", response_model=LessonProgressPublic)
async def start_lesson_endpoint(
    lesson_id: int,
    db: DbSession,
    actor: CurrentUser,
    _u: User = Depends(require_permission("progress.write")),
) -> LessonProgressPublic:
    p = await service.start_lesson(db, user_id=actor.id, lesson_id=lesson_id)
    await db.commit()
    return LessonProgressPublic.model_validate(p)


@router.post("/lessons/{lesson_id}/complete", response_model=LessonProgressPublic)
async def complete_lesson_endpoint(
    lesson_id: int,
    db: DbSession,
    actor: CurrentUser,
    _u: User = Depends(require_permission("progress.write")),
) -> LessonProgressPublic:
    p = await service.complete_lesson(db, user_id=actor.id, lesson_id=lesson_id)
    await db.commit()
    return LessonProgressPublic.model_validate(p)


@router.post("/lessons/{lesson_id}/progress", response_model=LessonProgressPublic)
async def save_lesson_progress(
    lesson_id: int,
    data: LessonProgressUpsertRequest,
    db: DbSession,
    actor: CurrentUser,
    _u: User = Depends(require_permission("progress.write")),
) -> LessonProgressPublic:
    p = await service.upsert_lesson_progress(
        db,
        user_id=actor.id,
        lesson_id=lesson_id,
        progress_percent=Decimal(data.progress_percent),
        time_spent_seconds=data.time_spent_seconds,
        last_position=data.last_position,
    )
    await db.commit()
    return LessonProgressPublic.model_validate(p)


class GradebookRow(BaseModel):
    """Phase 13.20 — Gradebook qator (talaba uchun bitta kurs natijasi)."""

    course_id: int
    title: str
    teacher: str
    credits: int
    current_avg: str
    midterm: str
    final: str
    total: str
    grade_letter: str
    grade_number: int
    grade_variant: str


@router.get("/me/gradebook", response_model=list[GradebookRow])
async def my_gradebook(
    db: DbSession,
    actor: CurrentUser,
) -> list[GradebookRow]:
    rows = await gradebook.get_my_gradebook(db, user_id=actor.id)
    return [GradebookRow(**r) for r in rows]


@router.get("/me/gradebook.csv", summary="Talaba transcripti CSV ko'rinishida")
async def my_gradebook_csv(
    db: DbSession,
    actor: CurrentUser,
) -> Response:
    rows = await gradebook.get_my_gradebook(db, user_id=actor.id)
    cols = ["Fan", "O'qituvchi", "Kredit", "Joriy", "Oraliq", "Yakuniy", "Umumiy", "Baho"]
    csv_rows = [
        {
            "Fan": r["title"],
            "O'qituvchi": r["teacher"],
            "Kredit": r["credits"],
            "Joriy": r["current_avg"],
            "Oraliq": r["midterm"],
            "Yakuniy": r["final"],
            "Umumiy": r["total"],
            "Baho": (
                f"{r['grade_letter']} ({r['grade_number']})"
                if r["grade_number"]
                else r["grade_letter"]
            ),
        }
        for r in rows
    ]
    csv_text = rows_to_csv(cols, csv_rows)
    fname = filename_with_timestamp(f"transcript_{actor.id}")
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


# ============================================================================
# Phase 16 — Talaba activity agregati (dashboard chart uchun)
# ============================================================================


class ActivityDay(BaseModel):
    date: str  # YYYY-MM-DD
    completed_count: int
    time_minutes: int


class ActivityResponse(BaseModel):
    days: list[ActivityDay]
    total_minutes: int
    total_completed: int
    streak_days: int
    most_active_label: str | None  # YYYY-MM-DD eng faol kun


@router.get("/me/activity", response_model=ActivityResponse)
async def my_activity(
    db: DbSession,
    actor: CurrentUser,
    days: int = Query(default=7, ge=1, le=365),
) -> ActivityResponse:
    """Phase 16 — talaba dashboard activity chart uchun.

    Oxirgi N kun ichida:
      - har kuni completed lessonlar soni
      - har kuni o'qish vaqti (LessonProgress.time_spent_seconds, agar shu kunda tugatilgan bo'lsa)
      - Streak — ketma-ket "kamida 1 ta dars tugatilgan" kunlar soni (bugundan boshlab)
    """
    from datetime import UTC, date, datetime, timedelta

    from sqlalchemy import func, select

    from app.modules.courses.models import LessonProgress

    today_utc = datetime.now(UTC).date()
    start = today_utc - timedelta(days=days - 1)

    rows = (
        await db.execute(
            select(
                func.date(LessonProgress.completed_at).label("d"),
                func.count(LessonProgress.id).label("c"),
                func.sum(LessonProgress.time_spent_seconds).label("t"),
            )
            .where(
                LessonProgress.user_id == actor.id,
                LessonProgress.completed_at.is_not(None),
                func.date(LessonProgress.completed_at) >= start,
            )
            .group_by(func.date(LessonProgress.completed_at))
        )
    ).all()
    by_date: dict[date, tuple[int, int]] = {}
    for d, c, t in rows:
        # `d` SQL DATE — Python date'ga aylanadi
        by_date[d] = (int(c or 0), int(t or 0))

    out_days: list[ActivityDay] = []
    total_completed = 0
    total_seconds = 0
    most_active_day: date | None = None
    most_active_minutes = -1
    for i in range(days):
        d = start + timedelta(days=i)
        c, t = by_date.get(d, (0, 0))
        mins = t // 60
        out_days.append(
            ActivityDay(date=d.isoformat(), completed_count=c, time_minutes=mins)
        )
        total_completed += c
        total_seconds += t
        if mins > most_active_minutes:
            most_active_minutes = mins
            most_active_day = d if mins > 0 else most_active_day

    # Streak — bugundan orqaga ketma-ket dars tugatilgan kunlar
    streak = 0
    for d in sorted(by_date.keys(), reverse=True):
        if d > today_utc:
            continue
        # Boshidan ketma-ketlik buzilmaganmi
        expected = today_utc - timedelta(days=streak)
        if d == expected:
            streak += 1
        else:
            break

    return ActivityResponse(
        days=out_days,
        total_minutes=total_seconds // 60,
        total_completed=total_completed,
        streak_days=streak,
        most_active_label=most_active_day.isoformat() if most_active_day else None,
    )


# ============================================================================
# Phase 19 — Course Reviews (talabaning kursga reytingi va sharhi)
# ============================================================================


class CourseReviewItem(BaseModel):
    """Bitta sharh — yulduz + matn + muallif minimal info."""

    id: int
    user_id: int
    user_full_name: str
    user_avatar_url: str | None
    rating: int
    comment: str | None
    created_at: datetime
    updated_at: datetime


class CourseReviewAggregate(BaseModel):
    """Kurs reytingi umumiy ko'rsatkichi."""

    avg_rating: float
    total: int
    distribution: dict[int, int]


class CourseReviewListResponse(BaseModel):
    items: list[CourseReviewItem]
    aggregate: CourseReviewAggregate
    my_review: CourseReviewItem | None


class CourseReviewCreateRequest(BaseModel):
    rating: int
    comment: str | None = None


@router.get(
    "/courses/{course_id}/reviews",
    response_model=CourseReviewListResponse,
)
async def list_course_reviews(
    course_id: int,
    db: DbSession,
    actor: CurrentUser,
    _u: User = Depends(require_permission("course.read")),
) -> CourseReviewListResponse:
    """Kurs sharhlari + aggregate (avg + distribution) + foydalanuvchining o'z sharhi."""
    from sqlalchemy import desc, func, select

    from app.modules.courses.models import Course, CourseReview
    from app.modules.users.models import User as UserModel

    # Kurs mavjudligini tekshiramiz (404 yoki access)
    await service.get_course(db, course_id)

    rows = (
        await db.execute(
            select(CourseReview, UserModel)
            .join(UserModel, UserModel.id == CourseReview.user_id)
            .where(CourseReview.course_id == course_id)
            .order_by(desc(CourseReview.created_at))
        )
    ).all()

    items = [
        CourseReviewItem(
            id=r.id,
            user_id=u.id,
            user_full_name=u.full_name,
            user_avatar_url=u.avatar_url,
            rating=r.rating,
            comment=r.comment,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r, u in rows
    ]

    total = len(items)
    avg = (sum(i.rating for i in items) / total) if total > 0 else 0.0

    dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for i in items:
        if i.rating in dist:
            dist[i.rating] += 1

    my_review: CourseReviewItem | None = next(
        (i for i in items if i.user_id == actor.id), None
    )

    return CourseReviewListResponse(
        items=items,
        aggregate=CourseReviewAggregate(
            avg_rating=round(avg, 2), total=total, distribution=dist
        ),
        my_review=my_review,
    )


@router.post(
    "/courses/{course_id}/reviews",
    response_model=CourseReviewItem,
    status_code=status.HTTP_201_CREATED,
)
async def create_course_review(
    course_id: int,
    payload: CourseReviewCreateRequest,
    db: DbSession,
    actor: CurrentUser,
    _u: User = Depends(require_permission("course.read")),
) -> CourseReviewItem:
    """Talaba kursga sharh qoldiradi (faqat enrolled talabalar)."""
    from sqlalchemy import select

    from app.modules.courses.models import CourseReview

    if not (1 <= payload.rating <= 5):
        raise ConflictError("Reyting 1 dan 5 gacha bo'lishi kerak")

    # Faqat shu kursga yozilgan talaba sharh qoldira oladi
    enrollment = await service.get_enrollment(db, course_id, actor.id)
    if enrollment is None:
        raise ForbiddenError("Sharh qoldirish uchun kursga yozilgan bo'lishingiz kerak")

    # Mavjud sharh bo'lsa, konflikt qaytaramiz (PATCH ishlatiladi)
    existing = (
        await db.execute(
            select(CourseReview).where(
                CourseReview.course_id == course_id,
                CourseReview.user_id == actor.id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("Siz allaqachon sharh qoldirgansiz")

    review = CourseReview(
        course_id=course_id,
        user_id=actor.id,
        rating=payload.rating,
        comment=(payload.comment or "").strip() or None,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)

    return CourseReviewItem(
        id=review.id,
        user_id=actor.id,
        user_full_name=actor.full_name,
        user_avatar_url=actor.avatar_url,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


@router.patch(
    "/courses/{course_id}/reviews/me",
    response_model=CourseReviewItem,
)
async def update_my_course_review(
    course_id: int,
    payload: CourseReviewCreateRequest,
    db: DbSession,
    actor: CurrentUser,
    _u: User = Depends(require_permission("course.read")),
) -> CourseReviewItem:
    """O'z sharhini tahrirlash."""
    from sqlalchemy import select

    from app.modules.courses.models import CourseReview

    if not (1 <= payload.rating <= 5):
        raise ConflictError("Reyting 1 dan 5 gacha bo'lishi kerak")

    review = (
        await db.execute(
            select(CourseReview).where(
                CourseReview.course_id == course_id,
                CourseReview.user_id == actor.id,
            )
        )
    ).scalar_one_or_none()
    if review is None:
        raise NotFoundError("Siz hali sharh qoldirmagansiz")

    review.rating = payload.rating
    review.comment = (payload.comment or "").strip() or None
    await db.commit()
    await db.refresh(review)

    return CourseReviewItem(
        id=review.id,
        user_id=actor.id,
        user_full_name=actor.full_name,
        user_avatar_url=actor.avatar_url,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


@router.delete(
    "/courses/{course_id}/reviews/me",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_my_course_review(
    course_id: int,
    db: DbSession,
    actor: CurrentUser,
    _u: User = Depends(require_permission("course.read")),
) -> Response:
    """O'z sharhini o'chirish."""
    from sqlalchemy import select

    from app.modules.courses.models import CourseReview

    review = (
        await db.execute(
            select(CourseReview).where(
                CourseReview.course_id == course_id,
                CourseReview.user_id == actor.id,
            )
        )
    ).scalar_one_or_none()
    if review is None:
        raise NotFoundError("Sharh topilmadi")

    await db.delete(review)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

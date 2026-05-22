"""Courses endpointlari (Phase 3b).

Group:
- Course (8): list, create, get, get-by-slug, patch, delete, publish, unpublish
- Module (5): list, create, patch, delete, reorder
- Lesson (6): list, create, get, patch, delete, reorder
- Enrollment (5): self-enroll, self-unenroll, list-students, add-student, remove-student
- Progress (4): my-progress, start, complete, save
"""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel

from app.core.csv_export import filename_with_timestamp, rows_to_csv
from app.core.exceptions import ConflictError, ForbiddenError
from app.modules.auth.dependencies import (
    CurrentUser,
    DbSession,
    RedisClient,
    require_permission,
)
from app.modules.courses import gradebook, service
from app.modules.courses.schemas import (
    CourseCreateRequest,
    CoursePublic,
    CourseProgressPublic,
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

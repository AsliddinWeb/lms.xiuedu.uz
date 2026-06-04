"""Assignments endpointlari (Phase 4a — MVP).

10 ta endpoint:
    GET    /assignments                          — ro'yxat (filter)
    POST   /assignments                          — yaratish (pedagog)
    GET    /assignments/{id}                     — bitta topshiriq
    PATCH  /assignments/{id}                     — tahrir (pedagog)
    DELETE /assignments/{id}                     — soft-delete
    POST   /assignments/{id}/publish             — publish/unpublish (toggle)
    POST   /assignments/{id}/upload              — fayl yuklash (multipart, talaba)
    POST   /assignments/{id}/submissions         — topshirish (talaba)
    GET    /assignments/{id}/submissions         — submissionlar ro'yxati (pedagog)
    GET    /submissions/{id}                     — bitta submission (talaba o'zinikini, pedagog kursinikini)
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status

from app.core.exceptions import ForbiddenError
from app.core.storage import upload_object
from app.modules.assignments import service
from app.modules.assignments.schemas import (
    AnnotationsUpdateRequest,
    AppealCreateRequest,
    AppealPublic,
    AppealRespondRequest,
    AssignmentCreateRequest,
    AssignmentPublic,
    AssignmentPublishRequest,
    AssignmentUpdateRequest,
    GradeRequest,
    PaginatedAppeals,
    PaginatedAssignments,
    PaginatedRubrics,
    PaginatedSubmissions,
    PlagiarismCheckResult,
    RubricCreateRequest,
    RubricPublic,
    RubricUpdateRequest,
    SubmissionCreateRequest,
    SubmissionPublic,
    SubmissionUploadResponse,
)
from app.modules.auth.dependencies import (
    CurrentUser,
    DbSession,
    RedisClient,
    require_permission,
)
from app.modules.courses import service as courses_service
from app.modules.rbac.service import RBACService, has_permission
from app.modules.users.models import User

router = APIRouter()


# ============================================================================
# Helpers
# ============================================================================


async def _appeal_to_public(db, appeal) -> AppealPublic:
    """AppealPublic — student_full_name + reviewed_by_full_name bilan."""
    names = await service.load_user_names(
        db, [appeal.student_id, appeal.reviewed_by]
    )
    s = names.get(appeal.student_id)
    r = names.get(appeal.reviewed_by) if appeal.reviewed_by else None
    return AppealPublic(
        id=appeal.id,
        submission_id=appeal.submission_id,
        student_id=appeal.student_id,
        student_full_name=s[0] if s else None,
        student_email=s[1] if s else None,
        reason=appeal.reason,
        status=appeal.status,
        new_score=appeal.new_score,
        response=appeal.response,
        reviewed_by=appeal.reviewed_by,
        reviewed_by_full_name=r[0] if r else None,
        reviewed_at=appeal.reviewed_at,
        created_at=appeal.created_at,
    )


async def _submission_to_public(db, s) -> SubmissionPublic:
    """SubmissionPublic — user_full_name + graded_by_full_name bilan."""
    names = await service.load_user_names(db, [s.user_id, s.graded_by])
    u = names.get(s.user_id)
    g = names.get(s.graded_by) if s.graded_by else None
    base = SubmissionPublic.model_validate(s).model_dump()
    base["user_full_name"] = u[0] if u else None
    base["user_email"] = u[1] if u else None
    base["graded_by_full_name"] = g[0] if g else None
    return SubmissionPublic.model_validate(base)


async def _submissions_to_public(db, submissions: list) -> list[SubmissionPublic]:
    if not submissions:
        return []
    ids: list[int] = []
    for s in submissions:
        ids.append(s.user_id)
        if s.graded_by is not None:
            ids.append(s.graded_by)
    names = await service.load_user_names(db, ids)
    out: list[SubmissionPublic] = []
    for s in submissions:
        u = names.get(s.user_id)
        g = names.get(s.graded_by) if s.graded_by else None
        base = SubmissionPublic.model_validate(s).model_dump()
        base["user_full_name"] = u[0] if u else None
        base["user_email"] = u[1] if u else None
        base["graded_by_full_name"] = g[0] if g else None
        out.append(SubmissionPublic.model_validate(base))
    return out


async def _appeals_to_public(db, appeals: list) -> list[AppealPublic]:
    """Batch — bitta query bilan barcha user_id'lar uchun nomlarni o'qish."""
    if not appeals:
        return []
    ids: list[int] = []
    for a in appeals:
        ids.append(a.student_id)
        if a.reviewed_by is not None:
            ids.append(a.reviewed_by)
    names = await service.load_user_names(db, ids)
    out: list[AppealPublic] = []
    for a in appeals:
        s = names.get(a.student_id)
        r = names.get(a.reviewed_by) if a.reviewed_by else None
        out.append(
            AppealPublic(
                id=a.id,
                submission_id=a.submission_id,
                student_id=a.student_id,
                student_full_name=s[0] if s else None,
                student_email=s[1] if s else None,
                reason=a.reason,
                status=a.status,
                new_score=a.new_score,
                response=a.response,
                reviewed_by=a.reviewed_by,
                reviewed_by_full_name=r[0] if r else None,
                reviewed_at=a.reviewed_at,
                created_at=a.created_at,
            )
        )
    return out


# 50 MB default — assignmentdagi `max_file_size_mb` cheklov yana ham qisqartirishi mumkin
SUBMISSION_HARD_MAX_BYTES = 200 * 1024 * 1024  # absolyut cheklov (200 MB)
ALLOWED_SUBMISSION_MIME = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/zip",
    "application/x-zip-compressed",
    "application/x-7z-compressed",
    "application/x-tar",
    "application/gzip",
    "application/json",
    "text/plain",
    "text/csv",
    "text/markdown",
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "audio/mpeg",
    "audio/wav",
    "video/mp4",
    "video/webm",
}


# ============================================================================
# Helpers
# ============================================================================


async def _can_manage_assignment_course(
    db: DbSession, redis: RedisClient, user: User, course_id: int
) -> bool:
    """Course muallifi yoki platform.* /assignment.manage permission borlar boshqaradi."""
    course = await courses_service.get_course(db, course_id)
    if course.primary_author_id == user.id:
        return True
    rbac = RBACService(db, redis)
    perms = await rbac.get_user_permissions(user.id)
    return (
        has_permission(perms, "platform.*")
        or has_permission(perms, "assignment.manage")
    )


# ============================================================================
# Assignment CRUD
# ============================================================================


@router.get("/assignments", response_model=PaginatedAssignments)
async def list_assignments(
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("assignment.read")),
    course_id: int | None = Query(None),
    lesson_id: int | None = Query(None),
    is_published: bool | None = Query(None),
    only_active: bool = Query(
        False, description="Faqat hozirda topshirish ochiq bo'lganlari (talabalarga)"
    ),
    enrolled_user_id: int | None = Query(
        None,
        description=(
            "Faqat shu user yozilgan kurslarning topshiriqlari. 'me' tarjimasi:"
            " mine=true bilan yo'naltirish — pastdagi `mine` parametrni ishlating."
        ),
    ),
    mine: bool = Query(False, description="Joriy foydalanuvchi yozilgan kurslar bo'yicha"),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedAssignments:
    if mine:
        enrolled_user_id = actor.id
    items, total = await service.list_assignments(
        db,
        course_id=course_id,
        lesson_id=lesson_id,
        is_published=is_published,
        only_active=only_active,
        enrolled_user_id=enrolled_user_id,
        q=q,
        page=page,
        page_size=page_size,
    )
    return PaginatedAssignments(
        items=[AssignmentPublic.model_validate(a) for a in items], total=total
    )


@router.post(
    "/assignments",
    response_model=AssignmentPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_assignment(
    data: AssignmentCreateRequest,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("assignment.manage")),
) -> AssignmentPublic:
    if not await _can_manage_assignment_course(db, redis, actor, data.course_id):
        raise ForbiddenError("Bu kursga topshiriq qo'shish huquqi yo'q")
    a = await service.create_assignment(db, data, created_by=actor.id)
    await db.commit()
    return AssignmentPublic.model_validate(a)


@router.get("/assignments/{assignment_id}", response_model=AssignmentPublic)
async def get_assignment(
    assignment_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("assignment.read")),
) -> AssignmentPublic:
    return AssignmentPublic.model_validate(await service.get_assignment(db, assignment_id))


@router.patch("/assignments/{assignment_id}", response_model=AssignmentPublic)
async def update_assignment(
    assignment_id: int,
    data: AssignmentUpdateRequest,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("assignment.manage")),
) -> AssignmentPublic:
    a = await service.get_assignment(db, assignment_id)
    if not await _can_manage_assignment_course(db, redis, actor, a.course_id):
        raise ForbiddenError("Bu topshiriqni tahrirlash huquqi yo'q")
    a = await service.update_assignment(db, assignment_id, data)
    await db.commit()
    return AssignmentPublic.model_validate(a)


@router.delete(
    "/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_assignment(
    assignment_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("assignment.manage")),
) -> Response:
    a = await service.get_assignment(db, assignment_id)
    if not await _can_manage_assignment_course(db, redis, actor, a.course_id):
        raise ForbiddenError("Bu topshiriqni o'chirish huquqi yo'q")
    await service.delete_assignment(db, assignment_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/assignments/{assignment_id}/publish", response_model=AssignmentPublic)
async def publish_assignment(
    assignment_id: int,
    data: AssignmentPublishRequest,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("assignment.manage")),
) -> AssignmentPublic:
    a = await service.get_assignment(db, assignment_id)
    if not await _can_manage_assignment_course(db, redis, actor, a.course_id):
        raise ForbiddenError("Bu topshiriqni publish qilish huquqi yo'q")
    a = await service.set_published(db, assignment_id, is_published=data.is_published)
    await db.commit()
    return AssignmentPublic.model_validate(a)


# ============================================================================
# Upload (talaba)
# ============================================================================


@router.post(
    "/assignments/{assignment_id}/upload",
    response_model=SubmissionUploadResponse,
    summary="Topshiriq fayli yuklash (talaba). Submit'dan oldin qaytadigan URL'ni ishlatadi.",
)
async def upload_submission_file(
    assignment_id: int,
    db: DbSession,
    actor: CurrentUser,
    _u: User = Depends(require_permission("assignment.submit")),
    file: UploadFile = File(..., description="Yuklanadigan fayl"),
) -> SubmissionUploadResponse:
    a = await service.get_assignment(db, assignment_id)

    contents = await file.read()
    size_limit = min(a.max_file_size_mb * 1024 * 1024, SUBMISSION_HARD_MAX_BYTES)
    if len(contents) > size_limit:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Fayl hajmi {a.max_file_size_mb} MB dan oshmasligi kerak "
                f"(joriy: {len(contents)} bytes)"
            ),
        )

    ctype = (file.content_type or "application/octet-stream").lower()
    if ctype not in ALLOWED_SUBMISSION_MIME:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Fayl formati qo'llab-quvvatlanmaydi: {ctype}",
        )

    filename = file.filename or "submission"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"

    # Assignment'da allowed_file_types ko'rsatilgan bo'lsa ekstensiyani tekshirish
    if a.allowed_file_types and ext not in {e.lower() for e in a.allowed_file_types}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Fayl formati '{ext}' qabul qilinmaydi. Ruxsat etilgan: "
                f"{', '.join(sorted(a.allowed_file_types))}"
            ),
        )

    object_name = (
        f"submissions/{assignment_id}/{actor.id}/{secrets.token_hex(8)}.{ext}"
    )
    public_url = upload_object(
        object_name=object_name, data=contents, content_type=ctype
    )
    return SubmissionUploadResponse(
        name=filename, url=public_url, mime=ctype, size=len(contents)
    )


# ============================================================================
# Submissions
# ============================================================================


@router.post(
    "/assignments/{assignment_id}/submissions",
    response_model=SubmissionPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Topshirish (talaba)",
)
async def submit_assignment(
    assignment_id: int,
    data: SubmissionCreateRequest,
    db: DbSession,
    actor: CurrentUser,
    _u: User = Depends(require_permission("assignment.submit")),
) -> SubmissionPublic:
    s = await service.create_submission(
        db, assignment_id=assignment_id, user_id=actor.id, data=data
    )
    await db.commit()
    return await _submission_to_public(db, s)


@router.get(
    "/assignments/{assignment_id}/submissions",
    response_model=PaginatedSubmissions,
    summary="Topshiriq bo'yicha submissionlar (pedagog)",
)
async def list_assignment_submissions(
    assignment_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("assignment.grade")),
    user_id: int | None = Query(None),
    status_: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedSubmissions:
    a = await service.get_assignment(db, assignment_id)
    if not await _can_manage_assignment_course(db, redis, actor, a.course_id):
        raise ForbiddenError("Bu topshiriq submissionlarini ko'rish huquqi yo'q")
    items, total = await service.list_submissions(
        db,
        assignment_id=assignment_id,
        user_id=user_id,
        status_=status_,
        page=page,
        page_size=page_size,
    )
    return PaginatedSubmissions(
        items=await _submissions_to_public(db, items), total=total
    )


@router.get(
    "/assignments/{assignment_id}/my-submissions",
    response_model=list[SubmissionPublic],
    summary="Talaba o'z urinishlarini ko'radi (eng keyingi attempt boshida)",
)
async def list_my_submissions(
    assignment_id: int,
    db: DbSession,
    actor: CurrentUser,
    _u: User = Depends(require_permission("assignment.read")),
) -> list[SubmissionPublic]:
    # Mavjudligini tekshirish (404 mos)
    await service.get_assignment(db, assignment_id)
    items = await service.list_my_submissions(
        db, assignment_id=assignment_id, user_id=actor.id
    )
    return await _submissions_to_public(db, items)


@router.get(
    "/submissions/inbox",
    response_model=PaginatedSubmissions,
    summary="Pedagog uchun baholash kerak submissionlar (kurs muallifi scope)",
)
async def list_grading_inbox(
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("assignment.grade")),
    course_id: int | None = Query(None),
    assignment_id: int | None = Query(None),
    status_: str | None = Query(None, alias="status"),
    user_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedSubmissions:
    rbac = RBACService(db, redis)
    perms = await rbac.get_user_permissions(actor.id)
    is_platform = has_permission(perms, "platform.*")

    items, total = await service.list_inbox_for_teacher(
        db,
        teacher_id=actor.id,
        is_platform_admin=is_platform,
        course_id=course_id,
        assignment_id=assignment_id,
        status_=status_,
        user_id=user_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedSubmissions(
        items=await _submissions_to_public(db, items), total=total
    )


@router.get(
    "/submissions/{submission_id}",
    response_model=SubmissionPublic,
    summary="Bitta submission (talaba o'zinikini, pedagog kurs bo'yicha har birining)",
)
async def get_submission(
    submission_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("assignment.read")),
) -> SubmissionPublic:
    s = await service.get_submission(db, submission_id)

    # Ruxsat: o'z submissioni / kurs muallifi / admin
    if s.user_id != actor.id:
        a = await service.get_assignment(db, s.assignment_id)
        if not await _can_manage_assignment_course(db, redis, actor, a.course_id):
            raise ForbiddenError("Bu submissionni ko'rish huquqi yo'q")
    return await _submission_to_public(db, s)


# ============================================================================
# Rubric (Phase 4b)
# ============================================================================


@router.get("/rubrics", response_model=PaginatedRubrics)
async def list_rubrics(
    db: DbSession,
    _u: User = Depends(require_permission("rubric.read")),
    organization_id: int | None = Query(None),
    created_by: int | None = Query(None),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedRubrics:
    items, total = await service.list_rubrics(
        db,
        organization_id=organization_id,
        created_by=created_by,
        q=q,
        page=page,
        page_size=page_size,
    )
    return PaginatedRubrics(
        items=[RubricPublic.model_validate(r) for r in items], total=total
    )


@router.post(
    "/rubrics",
    response_model=RubricPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_rubric(
    data: RubricCreateRequest,
    db: DbSession,
    actor: CurrentUser,
    _u: User = Depends(require_permission("rubric.manage")),
) -> RubricPublic:
    r = await service.create_rubric(db, data, created_by=actor.id)
    await db.commit()
    return RubricPublic.model_validate(r)


@router.get("/rubrics/{rubric_id}", response_model=RubricPublic)
async def get_rubric(
    rubric_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("rubric.read")),
) -> RubricPublic:
    return RubricPublic.model_validate(await service.get_rubric(db, rubric_id))


@router.patch("/rubrics/{rubric_id}", response_model=RubricPublic)
async def update_rubric(
    rubric_id: int,
    data: RubricUpdateRequest,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("rubric.manage")),
) -> RubricPublic:
    r = await service.get_rubric(db, rubric_id)
    if r.created_by != actor.id:
        # Faqat muallif yoki platform.* tahrirlay oladi
        rbac = RBACService(db, redis)
        perms = await rbac.get_user_permissions(actor.id)
        if not has_permission(perms, "platform.*"):
            raise ForbiddenError("Bu rubricni tahrirlash huquqi yo'q (faqat muallif)")
    r = await service.update_rubric(db, rubric_id, data)
    await db.commit()
    return RubricPublic.model_validate(r)


@router.delete("/rubrics/{rubric_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rubric(
    rubric_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("rubric.manage")),
) -> Response:
    r = await service.get_rubric(db, rubric_id)
    if r.created_by != actor.id:
        rbac = RBACService(db, redis)
        perms = await rbac.get_user_permissions(actor.id)
        if not has_permission(perms, "platform.*"):
            raise ForbiddenError("Faqat rubric muallifi yoki platform admin o'chira oladi")
    await service.delete_rubric(db, rubric_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Grading + annotations (Phase 4b)
# ============================================================================


@router.post(
    "/submissions/{submission_id}/grade",
    response_model=SubmissionPublic,
    summary="Pedagog tomonidan submission baholash",
)
async def grade_submission(
    submission_id: int,
    data: GradeRequest,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("assignment.grade")),
) -> SubmissionPublic:
    s = await service.get_submission(db, submission_id)
    a = await service.get_assignment(db, s.assignment_id)
    if not await _can_manage_assignment_course(db, redis, actor, a.course_id):
        raise ForbiddenError("Bu submissionni baholash huquqi yo'q")
    s = await service.grade_submission(
        db, submission_id, data, grader_id=actor.id
    )
    await db.commit()
    return await _submission_to_public(db, s)


@router.put(
    "/submissions/{submission_id}/annotations",
    response_model=SubmissionPublic,
    summary="Inline annotationlarni to'liq almashtirish (pedagog)",
)
async def update_submission_annotations(
    submission_id: int,
    data: AnnotationsUpdateRequest,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("assignment.grade")),
) -> SubmissionPublic:
    s = await service.get_submission(db, submission_id)
    a = await service.get_assignment(db, s.assignment_id)
    if not await _can_manage_assignment_course(db, redis, actor, a.course_id):
        raise ForbiddenError("Bu submission annotationlarini tahrirlash huquqi yo'q")
    s = await service.update_annotations(db, submission_id, data)
    await db.commit()
    return await _submission_to_public(db, s)


# ============================================================================
# Plagiat (Phase 4e)
# ============================================================================


@router.post(
    "/submissions/{submission_id}/check-plagiarism",
    response_model=PlagiarismCheckResult,
    summary="Plagiat tekshiruvi (mock — Antiplag.uz keyingi sub-faza'da)",
)
async def check_plagiarism(
    submission_id: int,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("assignment.grade")),
) -> PlagiarismCheckResult:
    s = await service.get_submission(db, submission_id)
    a = await service.get_assignment(db, s.assignment_id)
    if not await _can_manage_assignment_course(db, redis, actor, a.course_id):
        raise ForbiddenError("Bu submission plagiat tekshiruvini ishga tushirish huquqi yo'q")
    s = await service.run_plagiarism_check(db, submission_id)
    await db.commit()
    return PlagiarismCheckResult(
        submission_id=s.id,
        plagiarism_score=s.plagiarism_score,
        plagiarism_report_url=s.plagiarism_report_url,
        plagiarism_flagged=s.plagiarism_flagged,
        plagiarism_checked_at=s.plagiarism_checked_at,
    )


# ============================================================================
# Appeals (Phase 4e)
# ============================================================================


@router.post(
    "/submissions/{submission_id}/appeal",
    response_model=AppealPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Bahoga apellyatsiya berish (talaba)",
)
async def create_appeal(
    submission_id: int,
    data: AppealCreateRequest,
    db: DbSession,
    actor: CurrentUser,
    _u: User = Depends(require_permission("appeal.create")),
) -> AppealPublic:
    ap = await service.create_appeal(
        db, submission_id, data, student_id=actor.id
    )
    await db.commit()
    return await _appeal_to_public(db, ap)


@router.get(
    "/appeals/my",
    response_model=list[AppealPublic],
    summary="Talaba o'z apellyatsiyalarini ko'radi",
)
async def list_my_appeals(
    db: DbSession,
    actor: CurrentUser,
    _u: User = Depends(require_permission("appeal.create")),
) -> list[AppealPublic]:
    items = await service.list_my_appeals(db, student_id=actor.id)
    return await _appeals_to_public(db, items)


@router.get(
    "/appeals",
    response_model=PaginatedAppeals,
    summary="Pedagog uchun apellyatsiyalar (course muallifi scope)",
)
async def list_appeals(
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("appeal.review")),
    status_: str | None = Query(None, alias="status"),
    student_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedAppeals:
    rbac = RBACService(db, redis)
    perms = await rbac.get_user_permissions(actor.id)
    is_platform = has_permission(perms, "platform.*")

    items, total = await service.list_appeals(
        db,
        teacher_id=actor.id,
        is_platform_admin=is_platform,
        status_=status_,
        student_id=student_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedAppeals(items=await _appeals_to_public(db, items), total=total)


@router.post(
    "/appeals/{appeal_id}/respond",
    response_model=AppealPublic,
    summary="Apellyatsiyaga javob (pedagog)",
)
async def respond_appeal(
    appeal_id: int,
    data: AppealRespondRequest,
    db: DbSession,
    actor: CurrentUser,
    redis: RedisClient,
    _u: User = Depends(require_permission("appeal.review")),
) -> AppealPublic:
    ap = await service.get_appeal(db, appeal_id)
    s = await service.get_submission(db, ap.submission_id)
    a = await service.get_assignment(db, s.assignment_id)
    if not await _can_manage_assignment_course(db, redis, actor, a.course_id):
        raise ForbiddenError("Bu apellyatsiyaga javob berish huquqi yo'q")
    ap = await service.respond_to_appeal(db, appeal_id, data, reviewer_id=actor.id)
    await db.commit()
    return await _appeal_to_public(db, ap)

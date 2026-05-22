"""Exams endpointlari — Phase 6a + 6b.

Phase 6a endpointlari:
    GET    /exams                              — ro'yxat (filter)
    POST   /exams                              — yaratish (pedagog)
    GET    /exams/{id}                         — bitta imtihon (with stats)
    PATCH  /exams/{id}                         — tahrir
    DELETE /exams/{id}                         — soft-delete (draft/archived bo'lsagina)
    POST   /exams/{id}/publish                 — publish (draft → published)
    POST   /exams/{id}/archive                 — archive (published → archived)

    GET    /exams/{id}/questions               — savollar ro'yxati
    POST   /exams/{id}/questions               — savol qo'shish
    POST   /exams/{id}/questions/reorder       — tartibni o'zgartirish

    GET    /questions/{id}                     — bitta savol
    PATCH  /questions/{id}                     — tahrir
    DELETE /questions/{id}                     — o'chirish

Phase 6b endpointlari:
    POST   /exams/{id}/start                   — talaba urinishni boshlaydi
    GET    /exams/{id}/my-attempts             — talaba o'z urinishlari
    GET    /exams/{id}/attempts                — pedagog uchun barcha urinishlar (filter)

    GET    /attempts/{id}                      — attempt (savol + saqlangan javoblar)
    POST   /attempts/{id}/answer               — javob saqlash (autosave)
    POST   /attempts/{id}/submit               — talaba submit qiladi
    GET    /attempts/{id}/result               — natija (faqat submitted bo'lganda)

    POST   /attempts/{id}/grade                — pedagog manual baholash
    POST   /attempts/{id}/invalidate           — admin/pedagog rad etadi
"""

from __future__ import annotations

from decimal import Decimal

from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status

from app.core.csv_export import filename_with_timestamp, rows_to_csv
from app.core.storage import get_presigned_url
from app.modules.auth.dependencies import (
    CurrentUser,
    DbSession,
    RedisClient,
    require_permission,
)
from app.modules.exams import attempts as attempts_service
from app.modules.exams import code_grading as code_grading_service
from app.modules.exams import hemis_sync as hemis_sync_service
from app.modules.exams import proctoring as proctoring_service
from app.modules.exams import reports as reports_service
from app.modules.exams import service
from app.modules.exams.schemas import (
    AnswerPublic,
    AnswerSubmit,
    AttemptPublic,
    CodeRunRequest,
    CodeRunResponse,
    CodeRunResultItem,
    CodeTestCaseCreate,
    CodeTestCasePublic,
    CodeTestCaseUpdate,
    AttemptResult,
    AttemptStudentSummary,
    AttemptTakeView,
    ExamCreateRequest,
    ExamPublic,
    ExamUpdateRequest,
    GradeAttemptRequest,
    HemisSyncLogPublic,
    IdReferencePhotoPublic,
    InvalidateAttemptRequest,
    PaginatedAttempts,
    PaginatedExams,
    PaginatedHemisSyncLogs,
    ProctoringEventCreate,
    ProctoringEventPublic,
    ProctoringSnapshotPublic,
    QuestionCreate,
    QuestionPublic,
    QuestionReorderRequest,
    QuestionStudent,
    QuestionUpdate,
    ViolationScorePublic,
)
from app.modules.users.models import User

router = APIRouter()


def _to_exam_public(exam, total_q: int = 0, total_p: Decimal = Decimal("0")) -> ExamPublic:
    """Exam → ExamPublic + stats."""
    data = ExamPublic.model_validate(exam).model_copy(
        update={"total_questions": total_q, "total_points": total_p}
    )
    return data


def _sign(obj_key: str | None, ttl: int = 900) -> str | None:
    """Maxfiy obyekt uchun presigned URL — Phase 7b."""
    if not obj_key:
        return None
    try:
        return get_presigned_url(obj_key, ttl_seconds=ttl)
    except Exception:
        return None


# ============================================================================
# Exam
# ============================================================================


@router.get("/exams", response_model=PaginatedExams)
async def list_exams(
    db: DbSession,
    course_id: int | None = Query(default=None),
    lesson_id: int | None = Query(default=None),
    type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    _u: User = Depends(require_permission("exam.create")),
) -> PaginatedExams:
    items, total = await service.list_exams(
        db,
        course_id=course_id,
        lesson_id=lesson_id,
        type=type,
        status=status,
        q=q,
        page=page,
        page_size=page_size,
    )
    public_items = [
        _to_exam_public(
            ex,
            total_q=len(ex.questions) if ex.questions else 0,
            total_p=sum((q.points for q in (ex.questions or [])), Decimal("0")),
        )
        for ex in items
    ]
    return PaginatedExams(items=public_items, total=total)


@router.get("/exams/my", response_model=PaginatedExams)
async def list_my_exams(
    db: DbSession,
    user: CurrentUser,
    course_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    _u: User = Depends(require_permission("exam.attempt")),
) -> PaginatedExams:
    """Talaba ko'radigan ro'yxat: yozilgan kurslardagi published imtihonlar."""
    items, total = await service.list_exams_for_student(
        db, user.id, course_id=course_id, page=page, page_size=page_size
    )
    public_items = [
        _to_exam_public(
            ex,
            total_q=len(ex.questions) if ex.questions else 0,
            total_p=sum((q.points for q in (ex.questions or [])), Decimal("0")),
        )
        for ex in items
    ]
    return PaginatedExams(items=public_items, total=total)


@router.post("/exams", response_model=ExamPublic, status_code=status.HTTP_201_CREATED)
async def create_exam(
    payload: ExamCreateRequest,
    db: DbSession,
    user: CurrentUser,
    _u: User = Depends(require_permission("exam.create")),
) -> ExamPublic:
    exam = await service.create_exam(db, payload, created_by=user.id)
    await db.commit()
    return _to_exam_public(exam)


@router.get("/exams/{exam_id}", response_model=ExamPublic)
async def get_exam(
    exam_id: int,
    db: DbSession,
    redis: RedisClient,
    user: CurrentUser,
) -> ExamPublic:
    """Pedagog/admin uchun har qanday imtihon; talaba uchun faqat enrolled+published."""
    from app.core.exceptions import ForbiddenError, NotFoundError
    from app.modules.rbac.service import RBACService, has_permission

    exam, total_q, total_p = await service.get_exam_with_stats(db, exam_id)

    rbac = RBACService(db, redis)
    granted = await rbac.get_user_permissions(user.id)

    if has_permission(granted, "exam.create"):
        # Pedagog/admin — to'liq ko'rinish
        return _to_exam_public(exam, total_q=total_q, total_p=total_p)

    if has_permission(granted, "exam.attempt"):
        # Talaba — faqat published va enrolled kursdagi
        if exam.status != "published":
            raise NotFoundError("Imtihon topilmadi")
        from sqlalchemy import select
        from app.modules.courses.models import Enrollment

        enrolled = (
            await db.execute(
                select(Enrollment.id).where(
                    Enrollment.user_id == user.id,
                    Enrollment.course_id == exam.course_id,
                )
            )
        ).scalar_one_or_none()
        if enrolled is None:
            raise NotFoundError("Imtihon topilmadi")
        return _to_exam_public(exam, total_q=total_q, total_p=total_p)

    raise ForbiddenError("Ruxsat yo'q")


@router.patch("/exams/{exam_id}", response_model=ExamPublic)
async def update_exam(
    exam_id: int,
    payload: ExamUpdateRequest,
    db: DbSession,
    _u: User = Depends(require_permission("exam.create")),
) -> ExamPublic:
    exam = await service.update_exam(db, exam_id, payload)
    await db.commit()
    _, total_q, total_p = await service.get_exam_with_stats(db, exam_id)
    return _to_exam_public(exam, total_q=total_q, total_p=total_p)


@router.delete("/exams/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exam(
    exam_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("exam.create")),
) -> Response:
    await service.delete_exam(db, exam_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/exams/{exam_id}/publish", response_model=ExamPublic)
async def publish_exam(
    exam_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("exam.create")),
) -> ExamPublic:
    exam = await service.publish_exam(db, exam_id)
    await db.commit()
    _, total_q, total_p = await service.get_exam_with_stats(db, exam_id)
    return _to_exam_public(exam, total_q=total_q, total_p=total_p)


@router.post("/exams/{exam_id}/archive", response_model=ExamPublic)
async def archive_exam(
    exam_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("exam.create")),
) -> ExamPublic:
    exam = await service.archive_exam(db, exam_id)
    await db.commit()
    _, total_q, total_p = await service.get_exam_with_stats(db, exam_id)
    return _to_exam_public(exam, total_q=total_q, total_p=total_p)


# ============================================================================
# Question (nested under Exam)
# ============================================================================


@router.get("/exams/{exam_id}/questions", response_model=list[QuestionPublic])
async def list_questions(
    exam_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("exam.create")),
) -> list[QuestionPublic]:
    qs = await service.list_questions(db, exam_id)
    return [QuestionPublic.model_validate(q) for q in qs]


@router.post(
    "/exams/{exam_id}/questions",
    response_model=QuestionPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_question(
    exam_id: int,
    payload: QuestionCreate,
    db: DbSession,
    _u: User = Depends(require_permission("exam.create")),
) -> QuestionPublic:
    q = await service.create_question(db, exam_id, payload)
    await db.commit()
    return QuestionPublic.model_validate(q)


@router.post("/exams/{exam_id}/questions/reorder", response_model=list[QuestionPublic])
async def reorder_questions(
    exam_id: int,
    payload: QuestionReorderRequest,
    db: DbSession,
    _u: User = Depends(require_permission("exam.create")),
) -> list[QuestionPublic]:
    qs = await service.reorder_questions(db, exam_id, payload.ids)
    await db.commit()
    return [QuestionPublic.model_validate(q) for q in qs]


@router.get("/questions/{question_id}", response_model=QuestionPublic)
async def get_question(
    question_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("exam.create")),
) -> QuestionPublic:
    q = await service.get_question(db, question_id)
    return QuestionPublic.model_validate(q)


@router.patch("/questions/{question_id}", response_model=QuestionPublic)
async def update_question(
    question_id: int,
    payload: QuestionUpdate,
    db: DbSession,
    _u: User = Depends(require_permission("exam.create")),
) -> QuestionPublic:
    q = await service.update_question(db, question_id, payload)
    await db.commit()
    return QuestionPublic.model_validate(q)


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("exam.create")),
) -> Response:
    await service.delete_question(db, question_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Attempts (Phase 6b)
# ============================================================================


def _take_view(
    attempt, exam, questions, saved_answers
) -> AttemptTakeView:
    return AttemptTakeView(
        id=attempt.id,
        exam_id=attempt.exam_id,
        attempt_number=attempt.attempt_number,
        status=attempt.status,
        started_at=attempt.started_at,
        deadline_at=attempt.deadline_at,
        duration_minutes=exam.duration_minutes,
        questions=[QuestionStudent.model_validate(q) for q in questions],
        saved_answers=[
            AnswerSubmit(
                question_id=a.question_id,
                selected_option_ids=a.selected_option_ids,
                text_answer=a.text_answer,
                code_answer=a.code_answer,
                file_url=a.file_url,
                file_size_bytes=a.file_size_bytes,
            )
            for a in saved_answers
        ],
    )


def _result_view(attempt, show_answers: bool) -> AttemptResult:
    return AttemptResult(
        id=attempt.id,
        exam_id=attempt.exam_id,
        attempt_number=attempt.attempt_number,
        status=attempt.status,
        submitted_at=attempt.submitted_at,
        time_spent_seconds=attempt.time_spent_seconds,
        auto_score=attempt.auto_score,
        manual_score=attempt.manual_score,
        total_score=attempt.total_score,
        max_score=attempt.max_score,
        percentage=attempt.percentage,
        passed=attempt.passed,
        answers=(
            [AnswerPublic.model_validate(a) for a in attempt.answers]
            if show_answers
            else []
        ),
    )


@router.post(
    "/exams/{exam_id}/start",
    response_model=AttemptTakeView,
    status_code=status.HTTP_201_CREATED,
)
async def start_attempt(
    exam_id: int,
    db: DbSession,
    user: CurrentUser,
    _u: User = Depends(require_permission("exam.attempt")),
) -> AttemptTakeView:
    attempt = await attempts_service.start_attempt(db, exam_id, user.id)
    await db.commit()
    attempt, exam, questions, saved = await attempts_service.get_take_view(
        db, attempt.id, user.id
    )
    return _take_view(attempt, exam, questions, saved)


@router.get("/exams/{exam_id}/my-attempts", response_model=list[AttemptStudentSummary])
async def list_my_attempts(
    exam_id: int,
    db: DbSession,
    user: CurrentUser,
    _u: User = Depends(require_permission("exam.attempt")),
) -> list[AttemptStudentSummary]:
    items = await attempts_service.list_user_attempts(db, exam_id, user.id)
    # Lazy auto-submit ham flush qilingan bo'lishi mumkin
    await db.commit()
    return [AttemptStudentSummary.model_validate(a) for a in items]


@router.get("/exams/{exam_id}/attempts", response_model=PaginatedAttempts)
async def list_exam_attempts(
    exam_id: int,
    db: DbSession,
    user_id: int | None = Query(default=None),
    attempt_status: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    _u: User = Depends(require_permission("exam.create")),
) -> PaginatedAttempts:
    items, total = await attempts_service.list_exam_attempts(
        db,
        exam_id,
        user_id=user_id,
        status=attempt_status,
        page=page,
        page_size=page_size,
    )
    return PaginatedAttempts(
        items=[AttemptPublic.model_validate(a) for a in items], total=total
    )


@router.get("/exams/{exam_id}/attempts.csv")
async def export_exam_attempts_csv(
    exam_id: int,
    db: DbSession,
    user_id: int | None = Query(default=None),
    attempt_status: str | None = Query(default=None, alias="status"),
    _u: User = Depends(require_permission("exam.create")),
) -> Response:
    """Phase 8f — Pedagog uchun imtihon urinishlari ro'yxati CSV faylda.

    Sahifalashsiz (10k gacha bir yo'la) — XIU bitta exam uchun bu yetarli.
    """
    items, _ = await attempts_service.list_exam_attempts(
        db,
        exam_id,
        user_id=user_id,
        status=attempt_status,
        page=1,
        page_size=10_000,
    )
    csv_data = [
        {
            "attempt_id": a.id,
            "user_id": a.user_id,
            "attempt_number": a.attempt_number,
            "status": a.status,
            "started_at": a.started_at.isoformat() if a.started_at else "",
            "submitted_at": a.submitted_at.isoformat() if a.submitted_at else "",
            "time_spent_seconds": a.time_spent_seconds,
            "total_score": str(a.total_score) if a.total_score is not None else "",
            "max_score": str(a.max_score) if a.max_score is not None else "",
            "percentage": str(a.percentage) if a.percentage is not None else "",
            "passed": "yes" if a.passed else ("no" if a.passed is False else ""),
            "violation_score": a.violation_score,
            "flagged": "yes" if a.flagged else "no",
            "smart_score": a.smart_score,
        }
        for a in items
    ]
    csv_text = rows_to_csv(
        [
            "attempt_id",
            "user_id",
            "attempt_number",
            "status",
            "started_at",
            "submitted_at",
            "time_spent_seconds",
            "total_score",
            "max_score",
            "percentage",
            "passed",
            "violation_score",
            "flagged",
            "smart_score",
        ],
        csv_data,
    )
    fname = filename_with_timestamp(f"exam_{exam_id}_attempts")
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


@router.get("/attempts/{attempt_id}", response_model=AttemptTakeView)
async def get_attempt(
    attempt_id: int,
    db: DbSession,
    user: CurrentUser,
    _u: User = Depends(require_permission("exam.attempt")),
) -> AttemptTakeView:
    attempt, exam, questions, saved = await attempts_service.get_take_view(
        db, attempt_id, user.id
    )
    await db.commit()
    return _take_view(attempt, exam, questions, saved)


@router.post("/attempts/{attempt_id}/answer", response_model=AnswerPublic)
async def save_answer(
    attempt_id: int,
    payload: AnswerSubmit,
    db: DbSession,
    user: CurrentUser,
    _u: User = Depends(require_permission("exam.attempt")),
) -> AnswerPublic:
    ans = await attempts_service.save_answer(db, attempt_id, user.id, payload)
    await db.commit()
    return AnswerPublic.model_validate(ans)


@router.post("/attempts/{attempt_id}/submit", response_model=AttemptResult)
async def submit_attempt(
    attempt_id: int,
    db: DbSession,
    user: CurrentUser,
    _u: User = Depends(require_permission("exam.attempt")),
) -> AttemptResult:
    attempt = await attempts_service.submit_attempt(db, attempt_id, user.id)
    await db.commit()
    _, show = await attempts_service.get_result(db, attempt.id, user.id)
    return _result_view(attempt, show)


@router.get("/attempts/{attempt_id}/result", response_model=AttemptResult)
async def get_attempt_result(
    attempt_id: int,
    db: DbSession,
    user: CurrentUser,
    _u: User = Depends(require_permission("exam.attempt")),
) -> AttemptResult:
    attempt, show = await attempts_service.get_result(db, attempt_id, user.id)
    await db.commit()
    return _result_view(attempt, show)


@router.post("/attempts/{attempt_id}/grade", response_model=AttemptPublic)
async def grade_attempt(
    attempt_id: int,
    payload: GradeAttemptRequest,
    db: DbSession,
    user: CurrentUser,
    _u: User = Depends(require_permission("exam.create")),
) -> AttemptPublic:
    attempt = await attempts_service.grade_attempt(
        db, attempt_id, grader_id=user.id, grades=payload.grades
    )
    await db.commit()
    await db.refresh(attempt)
    return AttemptPublic.model_validate(attempt)


@router.post("/attempts/{attempt_id}/invalidate", response_model=AttemptPublic)
async def invalidate_attempt(
    attempt_id: int,
    payload: InvalidateAttemptRequest,
    db: DbSession,
    _u: User = Depends(require_permission("exam.create")),
) -> AttemptPublic:
    attempt = await attempts_service.invalidate_attempt(
        db, attempt_id, reason=payload.reason
    )
    await db.commit()
    await db.refresh(attempt)
    return AttemptPublic.model_validate(attempt)


# ============================================================================
# Proctoring (Phase 6f)
# ============================================================================


@router.post(
    "/attempts/{attempt_id}/proctoring/event",
    response_model=ProctoringEventPublic,
    status_code=status.HTTP_201_CREATED,
)
async def post_proctoring_event(
    attempt_id: int,
    payload: ProctoringEventCreate,
    db: DbSession,
    user: CurrentUser,
    _u: User = Depends(require_permission("exam.attempt")),
) -> ProctoringEventPublic:
    event = await proctoring_service.log_event(
        db,
        attempt_id=attempt_id,
        user_id=user.id,
        event_type=payload.event_type,
        severity=payload.severity,
        metadata=payload.metadata,
        occurred_at=payload.occurred_at,
    )
    await db.commit()
    return ProctoringEventPublic.model_validate(event)


@router.get(
    "/attempts/{attempt_id}/proctoring/events",
    response_model=list[ProctoringEventPublic],
)
async def list_proctoring_events(
    attempt_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("exam.create")),
) -> list[ProctoringEventPublic]:
    events = await proctoring_service.list_events(db, attempt_id)
    return [ProctoringEventPublic.model_validate(e) for e in events]


@router.post(
    "/attempts/{attempt_id}/proctoring/snapshot",
    response_model=ProctoringSnapshotPublic,
    status_code=status.HTTP_201_CREATED,
)
async def upload_proctoring_snapshot(
    attempt_id: int,
    db: DbSession,
    user: CurrentUser,
    image: UploadFile = File(...),
    face_count: int | None = Form(default=None),
    face_match_score: float | None = Form(default=None),
    width: int | None = Form(default=None),
    height: int | None = Form(default=None),
    _u: User = Depends(require_permission("exam.attempt")),
) -> ProctoringSnapshotPublic:
    raw = await image.read()
    snap = await proctoring_service.upload_snapshot(
        db,
        attempt_id=attempt_id,
        user_id=user.id,
        image_bytes=raw,
        content_type=image.content_type or "image/jpeg",
        face_count=face_count,
        face_match_score=face_match_score,
        width=width,
        height=height,
    )
    await db.commit()
    result = ProctoringSnapshotPublic.model_validate(snap)
    result.url = _sign(snap.object_key) or result.url
    return result


@router.get(
    "/attempts/{attempt_id}/proctoring/snapshots",
    response_model=list[ProctoringSnapshotPublic],
)
async def list_proctoring_snapshots(
    attempt_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("exam.create")),
) -> list[ProctoringSnapshotPublic]:
    snaps = await proctoring_service.list_snapshots(db, attempt_id)
    out: list[ProctoringSnapshotPublic] = []
    for s in snaps:
        p = ProctoringSnapshotPublic.model_validate(s)
        p.url = _sign(s.object_key) or p.url
        out.append(p)
    return out


@router.get(
    "/attempts/{attempt_id}/proctoring/id-reference",
    response_model=IdReferencePhotoPublic | None,
)
async def get_id_reference(
    attempt_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("exam.create")),
) -> IdReferencePhotoPublic | None:
    ref = await proctoring_service.get_id_reference(db, attempt_id)
    if ref is None:
        return None
    result = IdReferencePhotoPublic.model_validate(ref)
    result.url = _sign(ref.object_key) or result.url
    return result


@router.post(
    "/attempts/{attempt_id}/proctoring/id-reference",
    response_model=IdReferencePhotoPublic,
    status_code=status.HTTP_201_CREATED,
)
async def upload_id_reference(
    attempt_id: int,
    db: DbSession,
    user: CurrentUser,
    image: UploadFile = File(...),
    _u: User = Depends(require_permission("exam.attempt")),
) -> IdReferencePhotoPublic:
    raw = await image.read()
    ref = await proctoring_service.upload_id_reference(
        db,
        attempt_id=attempt_id,
        user_id=user.id,
        image_bytes=raw,
        content_type=image.content_type or "image/jpeg",
    )
    await db.commit()
    result = IdReferencePhotoPublic.model_validate(ref)
    result.url = _sign(ref.object_key) or result.url
    return result


@router.get(
    "/attempts/{attempt_id}/proctoring/score",
    response_model=ViolationScorePublic,
)
async def get_violation_score(
    attempt_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("exam.create")),
) -> ViolationScorePublic:
    attempt = await attempts_service.get_attempt(db, attempt_id)
    return ViolationScorePublic(
        attempt_id=attempt.id,
        violation_score=attempt.violation_score,
        flagged=attempt.flagged,
    )


# ============================================================================
# Reports (Phase 6g)
# ============================================================================


@router.get("/reports/exams/summary")
async def reports_exam_summary(
    db: DbSession,
    course_id: int | None = Query(default=None),
    type: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    _u: User = Depends(require_permission("exam.create")),
) -> dict:
    return await reports_service.summary(
        db,
        course_id=course_id,
        type=type,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/reports/exams/csv")
async def reports_exam_csv(
    db: DbSession,
    course_id: int | None = Query(default=None),
    type: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    _u: User = Depends(require_permission("exam.create")),
) -> Response:
    report = await reports_service.summary(
        db,
        course_id=course_id,
        type=type,
        date_from=date_from,
        date_to=date_to,
    )
    csv_text = reports_service.to_csv(report)
    filename = f"exam_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ============================================================================
# HEMIS Sync (Phase 6g — DAK exams)
# ============================================================================


@router.post("/exams/{exam_id}/sync-hemis")
async def sync_hemis(
    exam_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("exam.create")),
) -> dict:
    """DAK imtihon baholarini HEMIS'ga yuborish (real client + retry + audit log)."""
    result = await hemis_sync_service.send_exam_grades(db, exam_id)
    await db.commit()
    return dict(result)


@router.get("/hemis/sync-log", response_model=PaginatedHemisSyncLogs)
async def list_hemis_sync_log(
    db: DbSession,
    sync_type: str | None = Query(default=None),
    sync_status: str | None = Query(default=None, alias="status"),
    target_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    _u: User = Depends(require_permission("exam.create")),
) -> PaginatedHemisSyncLogs:
    items, total = await hemis_sync_service.list_sync_logs(
        db,
        sync_type=sync_type,
        status=sync_status,
        target_id=target_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedHemisSyncLogs(
        items=[HemisSyncLogPublic.model_validate(i) for i in items], total=total
    )


@router.post("/hemis/sync-log/{log_id}/retry")
async def retry_hemis_sync(
    log_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("exam.create")),
) -> dict:
    """Failed bo'lgan sync logni qayta urinish."""
    result = await hemis_sync_service.retry_failed_log(db, log_id)
    await db.commit()
    return dict(result)


# ============================================================================
# Phase 10f — HEMIS data sync (admin orqali manual trigger)
# ============================================================================


@router.post("/hemis/sync/{entity}")
async def hemis_data_sync(
    entity: str,
    db: DbSession,
    _u: User = Depends(require_permission("platform.*")),
) -> dict:
    """HEMIS data sync (admin trigger).

    `entity` qiymatlari:
        - `students`   → /v1/data/student-list → User+Profile upsert
        - `employees`  → /v1/data/employee-list → User upsert
        - `departments` → /v1/data/department-list → Faculty upsert
        - `groups`     → /v1/data/group-list → AcademicGroup upsert
        - `all`        → barchasini ketma-ket (departments → groups → students → employees)

    `HEMIS_SYNC_ENABLED=False` bo'lsa, log 'skipped' bilan yoziladi (real HTTP yo'q).
    """
    from app.integrations.hemis.data_sync import SUPPORTED_SYNC_TYPES, run_sync

    if entity not in {*SUPPORTED_SYNC_TYPES, "all"}:
        from app.core.exceptions import ValidationError
        raise ValidationError(
            f"Sync turi noma'lum: {entity}. Ruxsat etilgan: "
            f"{', '.join((*SUPPORTED_SYNC_TYPES, 'all'))}"
        )

    result = await run_sync(db, entity)
    await db.commit()
    return dict(result)


# ============================================================================
# Code question test cases + run (Phase 9d)
# ============================================================================


@router.get(
    "/questions/{question_id}/test-cases",
    response_model=list[CodeTestCasePublic],
)
async def list_code_test_cases(
    question_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("exam.create")),
) -> list[CodeTestCasePublic]:
    items = await code_grading_service.list_test_cases(db, question_id)
    return [CodeTestCasePublic.model_validate(i) for i in items]


@router.post(
    "/questions/{question_id}/test-cases",
    response_model=CodeTestCasePublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_code_test_case(
    question_id: int,
    payload: CodeTestCaseCreate,
    db: DbSession,
    _u: User = Depends(require_permission("exam.create")),
) -> CodeTestCasePublic:
    tc = await code_grading_service.create_test_case(
        db,
        question_id,
        stdin=payload.stdin,
        expected_stdout=payload.expected_stdout,
        is_hidden=payload.is_hidden,
        weight=payload.weight,
        order_index=payload.order_index,
    )
    await db.commit()
    return CodeTestCasePublic.model_validate(tc)


@router.patch(
    "/code-test-cases/{test_case_id}",
    response_model=CodeTestCasePublic,
)
async def update_code_test_case(
    test_case_id: int,
    payload: CodeTestCaseUpdate,
    db: DbSession,
    _u: User = Depends(require_permission("exam.create")),
) -> CodeTestCasePublic:
    tc = await code_grading_service.update_test_case(
        db,
        test_case_id,
        stdin=payload.stdin,
        expected_stdout=payload.expected_stdout,
        is_hidden=payload.is_hidden,
        weight=payload.weight,
        order_index=payload.order_index,
    )
    await db.commit()
    return CodeTestCasePublic.model_validate(tc)


@router.delete(
    "/code-test-cases/{test_case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_code_test_case(
    test_case_id: int,
    db: DbSession,
    _u: User = Depends(require_permission("exam.create")),
) -> Response:
    await code_grading_service.delete_test_case(db, test_case_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/attempts/{attempt_id}/questions/{question_id}/run-code",
    response_model=CodeRunResponse,
)
async def run_code(
    attempt_id: int,
    question_id: int,
    payload: CodeRunRequest,
    db: DbSession,
    user: CurrentUser,
    _u: User = Depends(require_permission("exam.attempt")),
) -> CodeRunResponse:
    results = await code_grading_service.run_code_against_visible(
        db,
        attempt_id=attempt_id,
        user_id=user.id,
        question_id=question_id,
        code=payload.code,
    )
    items = [
        CodeRunResultItem(
            test_case_id=r.test_case_id,
            is_hidden=r.is_hidden,
            passed=r.passed,
            stdout=r.run.stdout,
            stderr=r.run.stderr,
            exit_code=r.run.exit_code,
            runtime_ms=r.run.runtime_ms,
            timed_out=r.run.timed_out,
            expected_stdout=r.expected_stdout if not r.is_hidden else None,
        )
        for r in results
    ]
    return CodeRunResponse(
        results=items,
        passed_count=sum(1 for r in items if r.passed),
        total=len(items),
    )

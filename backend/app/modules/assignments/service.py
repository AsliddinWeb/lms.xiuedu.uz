"""Assignments + Submissions service (Phase 4a).

Asosiy mantiq:
- Assignment CRUD (faqat course muallifi yoki platform.* perm bilan)
- Submission: talaba kursga yozilgan bo'lishi shart, max_attempts cheklov,
  late_submission_allowed va closed_at bo'yicha qabul qilish/rad etish
- is_late va days_late submit vaqtida hisoblanadi (tayyor bo'lganda
  Phase 4b grading score uchun ishlatadi)
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

import random

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.modules.assignments import plagiarism as plagiarism_module
from app.modules.assignments.models import (
    Assignment,
    GradeAppeal,
    Rubric,
    Submission,
)
from app.modules.assignments.schemas import (
    AnnotationsUpdateRequest,
    AppealCreateRequest,
    AppealRespondRequest,
    AssignmentCreateRequest,
    AssignmentUpdateRequest,
    GradeRequest,
    RubricCreateRequest,
    RubricUpdateRequest,
    SubmissionCreateRequest,
)
from app.modules.courses.models import Course, Enrollment, Lesson, Module
from app.modules.organizations.models import Organization
from app.modules.users.models import User


def _now() -> datetime:
    return datetime.now(UTC)


# ============================================================================
# Assignment
# ============================================================================


async def list_assignments(
    db: AsyncSession,
    *,
    course_id: int | None,
    lesson_id: int | None,
    is_published: bool | None,
    only_active: bool,
    enrolled_user_id: int | None,
    q: str | None,
    page: int,
    page_size: int,
) -> tuple[list[Assignment], int]:
    stmt = select(Assignment).where(Assignment.deleted_at.is_(None))
    if course_id is not None:
        stmt = stmt.where(Assignment.course_id == course_id)
    if lesson_id is not None:
        stmt = stmt.where(Assignment.lesson_id == lesson_id)
    if is_published is not None:
        stmt = stmt.where(Assignment.is_published.is_(is_published))
    if enrolled_user_id is not None:
        stmt = stmt.join(
            Enrollment,
            (Enrollment.course_id == Assignment.course_id)
            & (Enrollment.user_id == enrolled_user_id),
        )
    if only_active:
        # talabaga ko'rinadigan: published, available_from <= now, closed_at >= now (bo'lsa)
        now = _now()
        stmt = (
            stmt.where(Assignment.is_published.is_(True))
            .where(
                or_(
                    Assignment.available_from.is_(None),
                    Assignment.available_from <= now,
                )
            )
            .where(or_(Assignment.closed_at.is_(None), Assignment.closed_at >= now))
        )
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Assignment.title).like(like),
                func.lower(Assignment.description).like(like),
            )
        )

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = (
        stmt.order_by(desc(Assignment.id))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, int(total)


async def get_assignment(db: AsyncSession, assignment_id: int) -> Assignment:
    stmt = select(Assignment).where(
        Assignment.id == assignment_id, Assignment.deleted_at.is_(None)
    )
    a = (await db.execute(stmt)).scalar_one_or_none()
    if a is None:
        raise NotFoundError("Topshiriq topilmadi")
    return a


async def _validate_lesson_in_course(
    db: AsyncSession, lesson_id: int, course_id: int
) -> None:
    stmt = (
        select(Lesson.id)
        .join(Module, Module.id == Lesson.module_id)
        .where(Lesson.id == lesson_id, Module.course_id == course_id)
    )
    found = (await db.execute(stmt)).scalar_one_or_none()
    if found is None:
        raise ValidationError(
            f"Dars id={lesson_id} ushbu kursga tegishli emas"
        )


async def create_assignment(
    db: AsyncSession, data: AssignmentCreateRequest, *, created_by: int
) -> Assignment:
    if (await db.get(Course, data.course_id)) is None:
        raise NotFoundError(f"Kurs id={data.course_id} topilmadi")
    if data.lesson_id is not None:
        await _validate_lesson_in_course(db, data.lesson_id, data.course_id)
    if data.rubric_id is not None:
        if (await db.get(Rubric, data.rubric_id)) is None:
            raise NotFoundError(f"Rubric id={data.rubric_id} topilmadi")

    payload = data.model_dump()
    a = Assignment(created_by=created_by, **payload)
    db.add(a)
    await db.flush()
    await db.refresh(a)
    return a


async def update_assignment(
    db: AsyncSession, assignment_id: int, data: AssignmentUpdateRequest
) -> Assignment:
    a = await get_assignment(db, assignment_id)

    update = data.model_dump(exclude_unset=True)
    if "lesson_id" in update and update["lesson_id"] is not None:
        await _validate_lesson_in_course(db, update["lesson_id"], a.course_id)
    if "rubric_id" in update and update["rubric_id"] is not None:
        if (await db.get(Rubric, update["rubric_id"])) is None:
            raise NotFoundError(f"Rubric id={update['rubric_id']} topilmadi")

    # Cross-validation: due_date/closed_at after merge
    new_due = update.get("due_date", a.due_date)
    new_avail = update.get("available_from", a.available_from)
    new_closed = update.get("closed_at", a.closed_at)
    if new_avail is not None and new_avail >= new_due:
        raise ValidationError("available_from due_date'dan oldin bo'lishi kerak")
    if new_closed is not None and new_closed < new_due:
        raise ValidationError("closed_at due_date'dan keyin yoki teng bo'lishi kerak")

    new_max = update.get("max_score", a.max_score)
    new_pass = update.get("pass_score", a.pass_score)
    if new_pass is not None and Decimal(new_pass) > Decimal(new_max):
        raise ValidationError("pass_score max_score dan oshmasligi kerak")

    for k, v in update.items():
        setattr(a, k, v)
    await db.flush()
    await db.refresh(a)
    return a


async def delete_assignment(db: AsyncSession, assignment_id: int) -> None:
    a = await get_assignment(db, assignment_id)
    a.deleted_at = _now()
    await db.flush()


async def set_published(
    db: AsyncSession, assignment_id: int, *, is_published: bool
) -> Assignment:
    a = await get_assignment(db, assignment_id)
    a.is_published = is_published
    await db.flush()
    await db.refresh(a)
    return a


# ============================================================================
# Submission
# ============================================================================


def _calc_lateness(due_date: datetime, submitted_at: datetime) -> tuple[bool, int]:
    """is_late va days_late ni qaytaradi."""
    if submitted_at <= due_date:
        return False, 0
    delta = submitted_at - due_date
    days = math.ceil(delta.total_seconds() / 86400)
    return True, max(1, days)


async def _user_enrolled(
    db: AsyncSession, *, user_id: int, course_id: int
) -> bool:
    stmt = select(Enrollment.id).where(
        Enrollment.user_id == user_id, Enrollment.course_id == course_id
    )
    return (await db.execute(stmt)).scalar_one_or_none() is not None


async def list_submissions(
    db: AsyncSession,
    *,
    assignment_id: int,
    user_id: int | None,
    status_: str | None,
    page: int,
    page_size: int,
) -> tuple[list[Submission], int]:
    stmt = select(Submission).where(Submission.assignment_id == assignment_id)
    if user_id is not None:
        stmt = stmt.where(Submission.user_id == user_id)
    if status_ is not None:
        stmt = stmt.where(Submission.status == status_)

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = (
        stmt.order_by(desc(Submission.submitted_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, int(total)


async def get_submission(db: AsyncSession, submission_id: int) -> Submission:
    s = await db.get(Submission, submission_id)
    if s is None:
        raise NotFoundError("Topshiriq (submission) topilmadi")
    return s


async def get_my_submission(
    db: AsyncSession, *, assignment_id: int, user_id: int, attempt_number: int | None
) -> Submission | None:
    stmt = select(Submission).where(
        Submission.assignment_id == assignment_id, Submission.user_id == user_id
    )
    if attempt_number is not None:
        stmt = stmt.where(Submission.attempt_number == attempt_number)
    stmt = stmt.order_by(desc(Submission.attempt_number))
    return (await db.execute(stmt)).scalars().first()


async def list_inbox_for_teacher(
    db: AsyncSession,
    *,
    teacher_id: int,
    is_platform_admin: bool,
    course_id: int | None,
    assignment_id: int | None,
    status_: str | None,
    user_id: int | None,
    page: int,
    page_size: int,
) -> tuple[list[Submission], int]:
    """Pedagog uchun grading queue.

    Pedagog faqat o'zi muallifi bo'lgan kurslarning submissionlarini ko'radi
    (`Course.primary_author_id`). `platform.*` permissioniga ega user
    barcha kurslar submissionlarini ko'radi.
    """
    stmt = (
        select(Submission)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .join(Course, Course.id == Assignment.course_id)
        .where(Assignment.deleted_at.is_(None), Course.deleted_at.is_(None))
    )
    if not is_platform_admin:
        stmt = stmt.where(Course.primary_author_id == teacher_id)
    if course_id is not None:
        stmt = stmt.where(Assignment.course_id == course_id)
    if assignment_id is not None:
        stmt = stmt.where(Submission.assignment_id == assignment_id)
    if status_ is not None:
        stmt = stmt.where(Submission.status == status_)
    if user_id is not None:
        stmt = stmt.where(Submission.user_id == user_id)

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = (
        stmt.order_by(desc(Submission.submitted_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, int(total)


async def list_my_submissions(
    db: AsyncSession, *, assignment_id: int, user_id: int
) -> list[Submission]:
    """Talaba o'z urinishlarini tartib bilan (eng keyingi attempt yuqori)."""
    stmt = (
        select(Submission)
        .where(
            Submission.assignment_id == assignment_id,
            Submission.user_id == user_id,
        )
        .order_by(desc(Submission.attempt_number))
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_submission(
    db: AsyncSession,
    *,
    assignment_id: int,
    user_id: int,
    data: SubmissionCreateRequest,
) -> Submission:
    a = await get_assignment(db, assignment_id)

    if not a.is_published:
        raise ConflictError("Topshiriq hali published emas")

    now = _now()
    if a.available_from and a.available_from > now:
        raise ConflictError(
            f"Topshiriq {a.available_from.isoformat()} dan boshlab ochiladi"
        )
    if a.closed_at and a.closed_at < now:
        raise ConflictError("Topshiriq qabul qilish davri tugagan")

    if not await _user_enrolled(db, user_id=user_id, course_id=a.course_id):
        raise ForbiddenError("Topshiriq topshirish uchun kursga yozilish shart")

    # Type-aware validatsiya
    has_content = bool((data.content or "").strip())
    has_files = len(data.files) > 0
    if a.type == "essay" and not has_content:
        raise ValidationError("essay turidagi topshiriq uchun matn (content) majburiy")
    if a.type == "file" and not has_files:
        raise ValidationError("file turidagi topshiriq uchun fayl majburiy")

    # Allowed file types
    if a.type == "file" and a.allowed_file_types:
        allowed = {ext.lower() for ext in a.allowed_file_types}
        for f in data.files:
            ext = (f.name.rsplit(".", 1)[-1] if "." in f.name else "").lower()
            if ext not in allowed:
                raise ValidationError(
                    f"Fayl formati '{ext}' qabul qilinmaydi. Ruxsat etilgan: "
                    f"{', '.join(sorted(allowed))}"
                )

    # Late check
    is_late, days_late = _calc_lateness(a.due_date, now)
    if is_late and not a.late_submission_allowed:
        raise ConflictError(
            "Topshirish muddati o'tib ketgan, kech topshirish ruxsat etilmagan"
        )

    # Attempts cheklov
    last = await get_my_submission(
        db, assignment_id=assignment_id, user_id=user_id, attempt_number=None
    )
    next_attempt = 1 if last is None else last.attempt_number + 1
    if next_attempt > a.max_attempts:
        raise ConflictError(
            f"Maksimum urinishlar soni ({a.max_attempts}) tugadi"
        )
    if last is not None and last.status in {"submitted", "grading"}:
        raise ConflictError(
            "Oldingi urinishingiz hali tekshirilmoqda — natija kelguncha kuting"
        )

    s = Submission(
        assignment_id=assignment_id,
        user_id=user_id,
        attempt_number=next_attempt,
        content=data.content,
        files=[f.model_dump() for f in data.files],
        is_late=is_late,
        days_late=days_late,
        status="submitted",
    )
    db.add(s)
    await db.flush()

    # Phase 4e: avtomatik plagiat tekshiruvi (mock)
    if a.plagiarism_check_enabled:
        result = plagiarism_module.check_submission(
            submission_id=s.id,
            content=s.content,
            files=s.files,
        )
        s.plagiarism_score = result.similarity_percent
        s.plagiarism_report_url = result.report_url
        s.plagiarism_flagged = result.similarity_percent >= a.plagiarism_threshold
        s.plagiarism_checked_at = _now()
        await db.flush()

    await db.refresh(s)
    return s


# ============================================================================
# Rubric (Phase 4b)
# ============================================================================


def _criteria_total(criteria: list[dict]) -> Decimal:
    total = Decimal("0")
    for c in criteria:
        total += Decimal(str(c.get("max_points", 0)))
    return total


async def list_rubrics(
    db: AsyncSession,
    *,
    organization_id: int | None,
    created_by: int | None,
    q: str | None,
    page: int,
    page_size: int,
) -> tuple[list[Rubric], int]:
    stmt = select(Rubric).where(Rubric.deleted_at.is_(None))
    if organization_id is not None:
        stmt = stmt.where(Rubric.organization_id == organization_id)
    if created_by is not None:
        stmt = stmt.where(Rubric.created_by == created_by)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(Rubric.title).like(like))

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = (
        stmt.order_by(desc(Rubric.id))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, int(total)


async def get_rubric(db: AsyncSession, rubric_id: int) -> Rubric:
    stmt = select(Rubric).where(
        Rubric.id == rubric_id, Rubric.deleted_at.is_(None)
    )
    r = (await db.execute(stmt)).scalar_one_or_none()
    if r is None:
        raise NotFoundError("Rubric topilmadi")
    return r


async def create_rubric(
    db: AsyncSession, data: RubricCreateRequest, *, created_by: int
) -> Rubric:
    from app.core.tenant import get_xiu_org_id

    org_id = data.organization_id
    if org_id is None:
        org_id = await get_xiu_org_id(db)
    elif (await db.get(Organization, org_id)) is None:
        raise NotFoundError(f"Universitet id={org_id} topilmadi")

    criteria = [c.model_dump(mode="json") for c in data.criteria]
    total = _criteria_total(criteria)

    r = Rubric(
        title=data.title,
        description=data.description,
        organization_id=org_id,
        criteria=criteria,
        total_points=total,
        created_by=created_by,
    )
    db.add(r)
    await db.flush()
    await db.refresh(r)
    return r


async def update_rubric(
    db: AsyncSession, rubric_id: int, data: RubricUpdateRequest
) -> Rubric:
    r = await get_rubric(db, rubric_id)
    update = data.model_dump(exclude_unset=True)

    if "organization_id" in update and update["organization_id"] is not None:
        if (await db.get(Organization, update["organization_id"])) is None:
            raise NotFoundError(f"OTM id={update['organization_id']} topilmadi")

    if "criteria" in update and update["criteria"] is not None:
        criteria = [c if isinstance(c, dict) else c.model_dump(mode="json")
                    for c in (data.criteria or [])]
        update["criteria"] = criteria
        update["total_points"] = _criteria_total(criteria)

    for k, v in update.items():
        setattr(r, k, v)
    await db.flush()
    await db.refresh(r)
    return r


async def delete_rubric(db: AsyncSession, rubric_id: int) -> None:
    r = await get_rubric(db, rubric_id)
    r.deleted_at = _now()
    await db.flush()


# ============================================================================
# Grade flow (Phase 4b)
# ============================================================================


def _apply_late_penalty(
    score: Decimal, *, days_late: int, penalty_per_day: Decimal
) -> Decimal:
    """final_score = score × (1 − days_late × penalty/100), 0 dan past tushmaydi."""
    if days_late <= 0 or penalty_per_day <= 0:
        return score
    multiplier = Decimal("1") - (Decimal(days_late) * penalty_per_day / Decimal("100"))
    if multiplier < Decimal("0"):
        multiplier = Decimal("0")
    return (score * multiplier).quantize(Decimal("0.01"))


def _resolve_score_from_rubric(
    rubric: Rubric, rubric_scores: dict[str, Decimal]
) -> Decimal:
    """Rubric kriteriyalari bo'yicha ball yig'indisini tekshirib qaytaradi."""
    valid_keys = {c["key"]: Decimal(str(c["max_points"])) for c in rubric.criteria}
    unknown = set(rubric_scores.keys()) - set(valid_keys.keys())
    if unknown:
        raise ValidationError(
            f"Noma'lum rubric kriteriyalari: {', '.join(sorted(unknown))}"
        )
    total = Decimal("0")
    for key, pts in rubric_scores.items():
        if pts < 0:
            raise ValidationError(f"'{key}' ballar 0 dan past bo'lmasin")
        if pts > valid_keys[key]:
            raise ValidationError(
                f"'{key}' kriteriyasi: ball={pts} max={valid_keys[key]} dan oshmasin"
            )
        total += pts
    return total.quantize(Decimal("0.01"))


async def grade_submission(
    db: AsyncSession,
    submission_id: int,
    data: GradeRequest,
    *,
    grader_id: int,
) -> Submission:
    s = await get_submission(db, submission_id)
    a = await get_assignment(db, s.assignment_id)

    # Score ni aniqlaymiz
    if data.rubric_scores:
        if a.rubric_id is None:
            raise ValidationError(
                "Bu topshiriqqa rubric biriktirilmagan — to'g'ridan-to'g'ri score bering"
            )
        rubric = await get_rubric(db, a.rubric_id)
        score = _resolve_score_from_rubric(rubric, data.rubric_scores)
        rubric_scores = {k: float(v) for k, v in data.rubric_scores.items()}
    else:
        assert data.score is not None  # schema validator allaqachon tekshirgan
        score = Decimal(data.score).quantize(Decimal("0.01"))
        rubric_scores = {}

    if score > a.max_score:
        raise ValidationError(
            f"Ball ({score}) max_score ({a.max_score}) dan oshmasin"
        )

    final = _apply_late_penalty(
        score,
        days_late=s.days_late,
        penalty_per_day=Decimal(a.late_penalty_per_day),
    )

    s.score = score
    s.final_score = final
    s.feedback = data.feedback
    if data.grade_letter:
        s.grade_letter = data.grade_letter
    if rubric_scores:
        s.rubric_scores = rubric_scores
    s.status = "returned" if data.return_for_revision else "graded"
    s.graded_by = grader_id
    s.graded_at = _now()

    await db.flush()
    await db.refresh(s)
    return s


async def update_annotations(
    db: AsyncSession, submission_id: int, data: AnnotationsUpdateRequest
) -> Submission:
    s = await get_submission(db, submission_id)
    s.annotations = [a.model_dump(mode="json") for a in data.annotations]
    await db.flush()
    await db.refresh(s)
    return s


# ============================================================================
# Plagiat (Phase 4e)
# ============================================================================


async def run_plagiarism_check(
    db: AsyncSession, submission_id: int
) -> Submission:
    """Submission uchun plagiat tekshiruvi (manual, qaytarib bo'ladigan)."""
    s = await get_submission(db, submission_id)
    a = await get_assignment(db, s.assignment_id)

    result = plagiarism_module.check_submission(
        submission_id=s.id,
        content=s.content,
        files=s.files,
    )
    s.plagiarism_score = result.similarity_percent
    s.plagiarism_report_url = result.report_url
    s.plagiarism_flagged = result.similarity_percent >= a.plagiarism_threshold
    s.plagiarism_checked_at = _now()
    await db.flush()
    await db.refresh(s)
    return s


# ============================================================================
# Appeals (Phase 4e)
# ============================================================================


async def get_appeal(db: AsyncSession, appeal_id: int) -> GradeAppeal:
    ap = await db.get(GradeAppeal, appeal_id)
    if ap is None:
        raise NotFoundError("Apellyatsiya topilmadi")
    return ap


async def create_appeal(
    db: AsyncSession,
    submission_id: int,
    data: AppealCreateRequest,
    *,
    student_id: int,
) -> GradeAppeal:
    s = await get_submission(db, submission_id)
    if s.user_id != student_id:
        raise ForbiddenError("Faqat o'z bahosingizga apellyatsiya bera olasiz")
    if s.status not in {"graded", "returned"}:
        raise ConflictError("Faqat baholangan submissionga apellyatsiya berish mumkin")

    # Bitta submissionga 1 ta pending apellyatsiya cheklov
    existing_stmt = select(GradeAppeal).where(
        GradeAppeal.submission_id == submission_id,
        GradeAppeal.status == "pending",
    )
    if (await db.execute(existing_stmt)).scalar_one_or_none() is not None:
        raise ConflictError("Bu submissionga ochiq apellyatsiya bor")

    ap = GradeAppeal(
        submission_id=submission_id,
        student_id=student_id,
        reason=data.reason,
        status="pending",
    )
    db.add(ap)
    await db.flush()
    await db.refresh(ap)
    return ap


async def load_user_names(
    db: AsyncSession, user_ids: list[int]
) -> dict[int, tuple[str, str]]:
    """User id'lar uchun (full_name, email) lookup. Bo'sh ro'yxatda bo'sh dict."""
    cleaned = [int(uid) for uid in user_ids if uid is not None]
    if not cleaned:
        return {}
    rows = (
        await db.execute(select(User.id, User.full_name, User.email).where(User.id.in_(set(cleaned))))
    ).all()
    return {r.id: (r.full_name, r.email) for r in rows}


async def list_appeals(
    db: AsyncSession,
    *,
    teacher_id: int,
    is_platform_admin: bool,
    status_: str | None,
    student_id: int | None,
    page: int,
    page_size: int,
) -> tuple[list[GradeAppeal], int]:
    """Pedagog uchun apellyatsiyalar ro'yxati (course muallifi scope)."""
    stmt = (
        select(GradeAppeal)
        .join(Submission, Submission.id == GradeAppeal.submission_id)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .join(Course, Course.id == Assignment.course_id)
    )
    if not is_platform_admin:
        stmt = stmt.where(Course.primary_author_id == teacher_id)
    if status_ is not None:
        stmt = stmt.where(GradeAppeal.status == status_)
    if student_id is not None:
        stmt = stmt.where(GradeAppeal.student_id == student_id)

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = (
        stmt.order_by(desc(GradeAppeal.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, int(total)


async def list_my_appeals(
    db: AsyncSession, *, student_id: int
) -> list[GradeAppeal]:
    stmt = (
        select(GradeAppeal)
        .where(GradeAppeal.student_id == student_id)
        .order_by(desc(GradeAppeal.created_at))
    )
    return list((await db.execute(stmt)).scalars().all())


async def respond_to_appeal(
    db: AsyncSession,
    appeal_id: int,
    data: AppealRespondRequest,
    *,
    reviewer_id: int,
) -> GradeAppeal:
    ap = await get_appeal(db, appeal_id)
    if ap.status != "pending":
        raise ConflictError("Bu apellyatsiya allaqachon ko'rib chiqilgan")

    if data.status not in {"approved", "rejected"}:
        raise ValidationError(
            "status faqat 'approved' yoki 'rejected' bo'lishi mumkin"
        )

    if data.status == "approved":
        if data.new_score is None:
            raise ValidationError(
                "Approved apellyatsiya uchun new_score majburiy"
            )
        s = await get_submission(db, ap.submission_id)
        a = await get_assignment(db, s.assignment_id)
        if Decimal(data.new_score) > a.max_score:
            raise ValidationError(
                f"new_score ({data.new_score}) max_score ({a.max_score}) dan oshmasin"
            )
        # Submission score'ni yangilaymiz, late penalty qayta hisoblanadi
        new_score = Decimal(data.new_score).quantize(Decimal("0.01"))
        s.score = new_score
        s.final_score = _apply_late_penalty(
            new_score,
            days_late=s.days_late,
            penalty_per_day=Decimal(a.late_penalty_per_day),
        )
        s.graded_at = _now()
        s.graded_by = reviewer_id
        await db.flush()

    ap.status = data.status
    ap.new_score = (
        Decimal(data.new_score).quantize(Decimal("0.01"))
        if data.new_score is not None
        else None
    )
    ap.response = data.response
    ap.reviewed_by = reviewer_id
    ap.reviewed_at = _now()
    await db.flush()
    await db.refresh(ap)

    # Phase 7d — talabaga bildirishnoma
    try:
        from app.modules.notifications.service import notify_appeal_response
        await notify_appeal_response(
            db,
            appeal_id=ap.id,
            user_id=ap.student_id,
            decision=ap.status,
            submission_id=ap.submission_id,
        )
    except Exception:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).exception(
            "notify_appeal_response.failed appeal=%s", ap.id
        )
    return ap

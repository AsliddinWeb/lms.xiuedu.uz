"""Courses CRUD + progress service (Phase 3b).

Asosiy biznes-mantiq:
- Course / Module / Lesson CRUD (status workflow: draft → published → archived)
- Enrollment (self / manual)
- LessonProgress upsert (progress_percent + time + last_position)
- Course progress calculation: required lesson'lar bo'yicha foiz hisoblash;
  100% bo'lganda Enrollment.completion_status='completed' avtomatik qo'yiladi.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import and_, case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.academic.models import AcademicGroup, Subject
from app.modules.content.models import ContentItem
from app.modules.courses.models import (
    Course,
    Enrollment,
    Lesson,
    LessonProgress,
    Module,
)
from app.modules.courses.schemas import (
    CourseCreateRequest,
    CourseUpdateRequest,
    LessonCreateRequest,
    LessonUpdateRequest,
    ModuleCreateRequest,
    ModuleUpdateRequest,
)
from app.modules.organizations.models import Organization
from app.modules.users.models import User


def _now() -> datetime:
    return datetime.now(UTC)


COURSE_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"published", "archived"},
    "published": {"archived"},
    "archived": {"draft"},
}


# ============================================================================
# Course
# ============================================================================


async def list_courses(
    db: AsyncSession,
    *,
    type_: str | None,
    status_: str | None,
    subject_id: int | None,
    organization_id: int | None,
    language: str | None,
    primary_author_id: int | None,
    enrolled_user_id: int | None,
    q: str | None,
    page: int,
    page_size: int,
) -> tuple[list[Course], int]:
    stmt = select(Course).where(Course.deleted_at.is_(None))
    if type_ is not None:
        stmt = stmt.where(Course.type == type_)
    if status_ is not None:
        stmt = stmt.where(Course.status == status_)
    if subject_id is not None:
        stmt = stmt.where(Course.subject_id == subject_id)
    if organization_id is not None:
        stmt = stmt.where(Course.organization_id == organization_id)
    if language is not None:
        stmt = stmt.where(Course.language == language)
    if primary_author_id is not None:
        stmt = stmt.where(Course.primary_author_id == primary_author_id)
    if enrolled_user_id is not None:
        stmt = stmt.join(Enrollment, Enrollment.course_id == Course.id).where(
            Enrollment.user_id == enrolled_user_id
        )
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Course.title).like(like),
                func.lower(Course.description).like(like),
                func.lower(Course.slug).like(like),
            )
        )

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = (
        stmt.order_by(desc(Course.id))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, int(total)


async def get_course(db: AsyncSession, course_id: int) -> Course:
    stmt = select(Course).where(Course.id == course_id, Course.deleted_at.is_(None))
    c = (await db.execute(stmt)).scalar_one_or_none()
    if c is None:
        raise NotFoundError("Kurs topilmadi")
    return c


async def get_course_by_slug(db: AsyncSession, slug: str) -> Course:
    stmt = select(Course).where(Course.slug == slug, Course.deleted_at.is_(None))
    c = (await db.execute(stmt)).scalar_one_or_none()
    if c is None:
        raise NotFoundError("Kurs topilmadi")
    return c


async def create_course(
    db: AsyncSession, data: CourseCreateRequest, *, author_id: int
) -> Course:
    # Slug uniqueness
    dup = await db.execute(select(Course).where(Course.slug == data.slug))
    if dup.scalar_one_or_none():
        raise ConflictError(f"Kurs slug '{data.slug}' band")

    if data.subject_id is not None:
        if (await db.get(Subject, data.subject_id)) is None:
            raise NotFoundError(f"Fan id={data.subject_id} topilmadi")

    # Single-tenant: organization_id berilmagan bo'lsa avto XIU id
    payload = data.model_dump()
    if payload.get("organization_id") is None:
        from app.core.tenant import get_xiu_org_id
        payload["organization_id"] = await get_xiu_org_id(db)
    elif (await db.get(Organization, payload["organization_id"])) is None:
        raise NotFoundError(f"Universitet id={payload['organization_id']} topilmadi")

    course = Course(primary_author_id=author_id, status="draft", **payload)
    db.add(course)
    await db.flush()
    await db.refresh(course)
    return course


async def update_course(
    db: AsyncSession, course_id: int, data: CourseUpdateRequest
) -> Course:
    # Eslatma: published kursning metadatasi (nom, tavsif, maqsadlar, ...)
    # tahrirlanishi mumkin — slug CourseUpdateRequest'da yo'q, shuning uchun URL
    # buzilmaydi. Struktura (modul/dars) esa alohida funksiyalarda qulflanadi.
    course = await get_course(db, course_id)

    if data.subject_id is not None:
        if (await db.get(Subject, data.subject_id)) is None:
            raise NotFoundError(f"Fan id={data.subject_id} topilmadi")
    if data.organization_id is not None:
        if (await db.get(Organization, data.organization_id)) is None:
            raise NotFoundError(f"OTM id={data.organization_id} topilmadi")

    update = data.model_dump(exclude_unset=True)
    for k, v in update.items():
        setattr(course, k, v)
    await db.flush()
    await db.refresh(course)
    return course


async def delete_course(db: AsyncSession, course_id: int) -> None:
    course = await get_course(db, course_id)
    course.deleted_at = _now()
    await db.flush()


async def transition_course_status(
    db: AsyncSession, course_id: int, *, new_status: str
) -> Course:
    course = await get_course(db, course_id)
    allowed = COURSE_TRANSITIONS.get(course.status, set())
    if new_status not in allowed:
        allowed_text = ", ".join(sorted(allowed)) if allowed else "(hech narsa)"
        raise ValidationError(
            f"Kurs statusini '{course.status}' -> '{new_status}' o'zgartirish "
            f"ruxsat etilmagan. Ruxsat etilgan: {allowed_text}"
        )
    # Bo'sh kursni nashr qilib bo'lmaydi — kamida 1 modul va 1 dars bo'lishi shart
    if new_status == "published":
        module_ids = (
            await db.execute(
                select(Module.id).where(Module.course_id == course_id)
            )
        ).scalars().all()
        if not module_ids:
            raise ValidationError(
                "Kursni nashr qilish uchun kamida bitta modul bo'lishi shart"
            )
        lesson_count = (
            await db.execute(
                select(func.count())
                .select_from(Lesson)
                .where(Lesson.module_id.in_(module_ids))
            )
        ).scalar_one()
        if not lesson_count:
            raise ValidationError(
                "Kursni nashr qilish uchun kamida bitta dars bo'lishi shart"
            )
    course.status = new_status
    if new_status == "published":
        course.published_at = _now()
    await db.flush()
    await db.refresh(course)
    return course


# ============================================================================
# Module
# ============================================================================


async def list_modules(db: AsyncSession, course_id: int) -> list[Module]:
    await get_course(db, course_id)  # 404 check
    stmt = (
        select(Module)
        .where(Module.course_id == course_id)
        .order_by(Module.order_index, Module.id)
    )
    return list((await db.execute(stmt)).scalars().all())


async def get_module(db: AsyncSession, module_id: int) -> Module:
    m = await db.get(Module, module_id)
    if m is None:
        raise NotFoundError("Modul topilmadi")
    return m


async def _next_module_order(db: AsyncSession, course_id: int) -> int:
    stmt = select(func.coalesce(func.max(Module.order_index), -1)).where(
        Module.course_id == course_id
    )
    return int((await db.execute(stmt)).scalar_one()) + 1


async def create_module(
    db: AsyncSession, course_id: int, data: ModuleCreateRequest
) -> Module:
    await get_course(db, course_id)
    payload = data.model_dump(exclude_unset=True)
    if payload.get("order_index") is None:
        payload["order_index"] = await _next_module_order(db, course_id)
    m = Module(course_id=course_id, **payload)
    db.add(m)
    await db.flush()
    await db.refresh(m)
    return m


async def update_module(
    db: AsyncSession, module_id: int, data: ModuleUpdateRequest
) -> Module:
    m = await get_module(db, module_id)
    course = await get_course(db, m.course_id)
    if course.status == "published":
        raise ConflictError(
            "Published kursdagi modulni tahrirlab bo'lmaydi — avval unpublish qiling"
        )
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    await db.flush()
    await db.refresh(m)
    return m


async def delete_module(db: AsyncSession, module_id: int) -> None:
    m = await get_module(db, module_id)
    await db.delete(m)
    await db.flush()


async def reorder_modules(
    db: AsyncSession, course_id: int, *, ordered_ids: list[int]
) -> list[Module]:
    """Modullarni tartibga solish — barcha id course'ga tegishli bo'lishi shart."""
    await get_course(db, course_id)
    stmt = select(Module).where(Module.course_id == course_id)
    existing = list((await db.execute(stmt)).scalars().all())
    existing_ids = {m.id for m in existing}
    if set(ordered_ids) != existing_ids:
        raise ValidationError(
            "ordered_ids kursdagi modul id'lar bilan to'liq mos kelishi kerak"
        )
    by_id = {m.id: m for m in existing}
    for idx, mid in enumerate(ordered_ids):
        by_id[mid].order_index = idx
    await db.flush()
    return [by_id[i] for i in ordered_ids]


# ============================================================================
# Lesson
# ============================================================================


async def list_lessons(db: AsyncSession, module_id: int) -> list[Lesson]:
    await get_module(db, module_id)
    stmt = (
        select(Lesson)
        .where(Lesson.module_id == module_id)
        .order_by(Lesson.order_index, Lesson.id)
    )
    return list((await db.execute(stmt)).scalars().all())


async def get_lesson(db: AsyncSession, lesson_id: int) -> Lesson:
    l = await db.get(Lesson, lesson_id)
    if l is None:
        raise NotFoundError("Dars topilmadi")
    return l


async def _next_lesson_order(db: AsyncSession, module_id: int) -> int:
    stmt = select(func.coalesce(func.max(Lesson.order_index), -1)).where(
        Lesson.module_id == module_id
    )
    return int((await db.execute(stmt)).scalar_one()) + 1


async def create_lesson(
    db: AsyncSession, module_id: int, data: LessonCreateRequest
) -> Lesson:
    await get_module(db, module_id)
    if data.primary_content_id is not None:
        if (await db.get(ContentItem, data.primary_content_id)) is None:
            raise NotFoundError(f"Kontent id={data.primary_content_id} topilmadi")

    payload = data.model_dump(exclude_unset=True)
    if payload.get("order_index") is None:
        payload["order_index"] = await _next_lesson_order(db, module_id)
    lesson = Lesson(module_id=module_id, **payload)
    db.add(lesson)
    await db.flush()
    await db.refresh(lesson)
    return lesson


async def update_lesson(
    db: AsyncSession, lesson_id: int, data: LessonUpdateRequest
) -> Lesson:
    lesson = await get_lesson(db, lesson_id)
    module = await get_module(db, lesson.module_id)
    course = await get_course(db, module.course_id)
    if course.status == "published":
        raise ConflictError(
            "Published kursdagi darsni tahrirlab bo'lmaydi — avval unpublish qiling"
        )
    if data.primary_content_id is not None:
        if (await db.get(ContentItem, data.primary_content_id)) is None:
            raise NotFoundError(f"Kontent id={data.primary_content_id} topilmadi")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(lesson, k, v)
    await db.flush()
    await db.refresh(lesson)
    return lesson


async def delete_lesson(db: AsyncSession, lesson_id: int) -> None:
    lesson = await get_lesson(db, lesson_id)
    await db.delete(lesson)
    await db.flush()


async def reorder_lessons(
    db: AsyncSession, module_id: int, *, ordered_ids: list[int]
) -> list[Lesson]:
    await get_module(db, module_id)
    stmt = select(Lesson).where(Lesson.module_id == module_id)
    existing = list((await db.execute(stmt)).scalars().all())
    existing_ids = {l.id for l in existing}
    if set(ordered_ids) != existing_ids:
        raise ValidationError(
            "ordered_ids modulning dars id'lari bilan to'liq mos kelishi kerak"
        )
    by_id = {l.id: l for l in existing}
    for idx, lid in enumerate(ordered_ids):
        by_id[lid].order_index = idx
    await db.flush()
    return [by_id[i] for i in ordered_ids]


# ============================================================================
# Enrollment
# ============================================================================


async def get_enrollment(
    db: AsyncSession, course_id: int, user_id: int
) -> Enrollment | None:
    stmt = select(Enrollment).where(
        Enrollment.course_id == course_id, Enrollment.user_id == user_id
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def enroll_user(
    db: AsyncSession,
    course_id: int,
    *,
    user_id: int,
    method: str,
    enrolled_by: int | None,
) -> Enrollment:
    course = await get_course(db, course_id)
    if course.status != "published":
        raise ConflictError("Faqat published kursga yozilish mumkin")

    if (await db.get(User, user_id)) is None:
        raise NotFoundError(f"Foydalanuvchi id={user_id} topilmadi")

    existing = await get_enrollment(db, course_id, user_id)
    if existing is not None:
        raise ConflictError("Foydalanuvchi bu kursga allaqachon yozilgan")

    if course.max_students is not None:
        cnt = (
            await db.execute(
                select(func.count())
                .select_from(Enrollment)
                .where(Enrollment.course_id == course_id)
            )
        ).scalar_one()
        if int(cnt) >= course.max_students:
            raise ConflictError(
                f"Kurs to'lib qolgan (max {course.max_students} talaba)"
            )

    e = Enrollment(
        course_id=course_id,
        user_id=user_id,
        enrollment_method=method,
        enrolled_by=enrolled_by,
        completion_status="in_progress",
    )
    db.add(e)
    await db.flush()
    await db.refresh(e)
    return e


async def unenroll_user(db: AsyncSession, course_id: int, user_id: int) -> None:
    e = await get_enrollment(db, course_id, user_id)
    if e is None:
        raise NotFoundError("Yozilish topilmadi")
    await db.delete(e)
    await db.flush()


async def list_course_students(
    db: AsyncSession,
    course_id: int,
    *,
    page: int,
    page_size: int,
) -> tuple[list[tuple[Enrollment, User, Decimal]], int]:
    """Talabalar ro'yxati + har biri uchun progress foizi."""
    await get_course(db, course_id)

    base = (
        select(Enrollment, User)
        .join(User, User.id == Enrollment.user_id)
        .where(Enrollment.course_id == course_id)
    )

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    stmt = (
        base.order_by(Enrollment.enrolled_at)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).all()

    # Har talaba uchun progressni hisoblaymiz (kichik N — MVP'da yetadi)
    result: list[tuple[Enrollment, User, Decimal]] = []
    for enr, user in rows:
        pct = await calculate_course_progress(db, user_id=user.id, course_id=course_id)
        result.append((enr, user, pct["percent"]))
    return result, int(total)


async def list_my_students(
    db: AsyncSession,
    teacher_id: int,
    *,
    q: str | None = None,
    page: int,
    page_size: int,
) -> tuple[list, int]:
    """Pedagog barcha kurslari bo'yicha NOYOB talabalar (aggregate).

    Har talaba: ism/email/avatar/guruh + nechta kursda (shu pedagog), tugatgan
    kurslar soni, o'rtacha yakuniy baho. Qidiruv (ism/email) + pagination.
    """
    base = (
        select(
            User.id.label("user_id"),
            User.full_name,
            User.email,
            User.avatar_url,
            AcademicGroup.name.label("group_name"),
            func.count(Enrollment.id).label("course_count"),
            func.sum(
                case((Enrollment.completion_status == "completed", 1), else_=0)
            ).label("completed_count"),
            func.avg(Enrollment.final_grade).label("avg_grade"),
        )
        .select_from(Enrollment)
        .join(
            Course,
            and_(
                Course.id == Enrollment.course_id,
                Course.primary_author_id == teacher_id,
                Course.deleted_at.is_(None),
            ),
        )
        .join(User, User.id == Enrollment.user_id)
        .outerjoin(AcademicGroup, AcademicGroup.id == User.group_id)
    )
    if q and q.strip():
        like = f"%{q.strip()}%"
        base = base.where(or_(User.full_name.ilike(like), User.email.ilike(like)))

    grouped = base.group_by(
        User.id, User.full_name, User.email, User.avatar_url, AcademicGroup.name
    )
    total = (
        await db.execute(select(func.count()).select_from(grouped.subquery()))
    ).scalar_one()
    stmt = (
        grouped.order_by(User.full_name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).all()
    return list(rows), int(total)


async def get_my_student_courses(
    db: AsyncSession, teacher_id: int, user_id: int
) -> list[dict]:
    """Talabaning shu pedagog kurslaridagi yozilishlari + har biri progress/baho."""
    rows = (
        await db.execute(
            select(
                Course.id,
                Course.title,
                Enrollment.completion_status,
                Enrollment.final_grade,
                Enrollment.enrolled_at,
            )
            .select_from(Enrollment)
            .join(
                Course,
                and_(
                    Course.id == Enrollment.course_id,
                    Course.primary_author_id == teacher_id,
                    Course.deleted_at.is_(None),
                ),
            )
            .where(Enrollment.user_id == user_id)
            .order_by(Course.title)
        )
    ).all()
    out: list[dict] = []
    for cid, title, status, grade, enrolled in rows:
        pct = await calculate_course_progress(db, user_id=user_id, course_id=cid)
        out.append(
            {
                "course_id": cid,
                "course_title": title,
                "progress_percent": float(pct["percent"]),
                "completion_status": status,
                "final_grade": float(grade) if grade is not None else None,
                "enrolled_at": enrolled,
            }
        )
    return out


# ============================================================================
# Lesson progress
# ============================================================================


async def upsert_lesson_progress(
    db: AsyncSession,
    *,
    user_id: int,
    lesson_id: int,
    progress_percent: Decimal,
    time_spent_seconds: int | None,
    last_position: dict | None,
) -> LessonProgress:
    lesson = await get_lesson(db, lesson_id)

    # Talaba kursga yozilgan bo'lishi shart
    course_id = await _course_id_of_lesson(db, lesson)
    enrollment = await get_enrollment(db, course_id, user_id)
    if enrollment is None:
        raise ConflictError("Bu darsga kirish uchun avval kursga yozilish kerak")

    stmt = select(LessonProgress).where(
        LessonProgress.user_id == user_id, LessonProgress.lesson_id == lesson_id
    )
    progress = (await db.execute(stmt)).scalar_one_or_none()

    if progress is None:
        progress = LessonProgress(
            user_id=user_id,
            lesson_id=lesson_id,
            progress_percent=progress_percent,
            time_spent_seconds=time_spent_seconds or 0,
            last_position=last_position or {},
            started_at=_now(),
        )
        db.add(progress)
    else:
        # Foiz faqat oldinga harakat qiladi
        if progress_percent > progress.progress_percent:
            progress.progress_percent = progress_percent
        if time_spent_seconds is not None:
            progress.time_spent_seconds = max(progress.time_spent_seconds, time_spent_seconds)
        if last_position is not None:
            progress.last_position = last_position
        if progress.started_at is None:
            progress.started_at = _now()

    just_completed = (
        progress.progress_percent >= Decimal("100") and progress.completed_at is None
    )
    if just_completed:
        progress.completed_at = _now()

    await db.flush()

    # Phase 11e — lesson tugaganda gamification event
    if just_completed:
        from app.modules.gamification import service as gamif_service

        try:
            await gamif_service.award_event(
                db,
                user_id=user_id,
                event_type="lesson.completed",
                context={"lesson_id": lesson_id, "course_id": course_id},
                dedupe_key=f"lesson.completed:{user_id}:{lesson_id}",
            )
        except Exception:  # noqa: BLE001
            pass

    # Course progressini ham qayta hisoblaymiz — completed bo'lsa enrollment'ni yopadi
    await _maybe_complete_enrollment(db, user_id=user_id, course_id=course_id)
    await db.refresh(progress)
    return progress


async def start_lesson(
    db: AsyncSession, *, user_id: int, lesson_id: int
) -> LessonProgress:
    return await upsert_lesson_progress(
        db,
        user_id=user_id,
        lesson_id=lesson_id,
        progress_percent=Decimal("0"),
        time_spent_seconds=None,
        last_position=None,
    )


async def complete_lesson(
    db: AsyncSession, *, user_id: int, lesson_id: int
) -> LessonProgress:
    return await upsert_lesson_progress(
        db,
        user_id=user_id,
        lesson_id=lesson_id,
        progress_percent=Decimal("100"),
        time_spent_seconds=None,
        last_position=None,
    )


async def _course_id_of_lesson(db: AsyncSession, lesson: Lesson) -> int:
    module = await get_module(db, lesson.module_id)
    return module.course_id


async def calculate_course_progress(
    db: AsyncSession, *, user_id: int, course_id: int
) -> dict:
    """Kursdagi required lesson'lar bo'yicha foizni qaytaradi."""
    # Required lesson id'lari
    stmt = (
        select(Lesson.id)
        .join(Module, Module.id == Lesson.module_id)
        .where(
            Module.course_id == course_id,
            Lesson.is_required_for_completion.is_(True),
        )
    )
    required_ids = [row[0] for row in (await db.execute(stmt)).all()]
    total = len(required_ids)
    if total == 0:
        return {"completed": 0, "total": 0, "percent": Decimal("0")}

    completed_stmt = select(func.count()).where(
        and_(
            LessonProgress.user_id == user_id,
            LessonProgress.lesson_id.in_(required_ids),
            LessonProgress.progress_percent >= Decimal("100"),
        )
    )
    completed = int((await db.execute(completed_stmt)).scalar_one())
    pct = (Decimal(completed) / Decimal(total) * Decimal("100")).quantize(
        Decimal("0.01")
    )
    return {"completed": completed, "total": total, "percent": pct}


async def _maybe_complete_enrollment(
    db: AsyncSession, *, user_id: int, course_id: int
) -> None:
    """Agar talaba 100% required lesson'larni yakunlagan bo'lsa, completion_status'ni yopadi."""
    progress = await calculate_course_progress(db, user_id=user_id, course_id=course_id)
    if progress["total"] == 0 or progress["percent"] < Decimal("100"):
        return
    enrollment = await get_enrollment(db, course_id, user_id)
    if enrollment is None or enrollment.completion_status == "completed":
        return
    enrollment.completion_status = "completed"
    enrollment.completed_at = _now()
    await db.flush()

    # Phase 11d — sertifikat avtomatik beriladi (idempotent)
    from app.modules.certificates import service as certificates_service

    try:
        await certificates_service.issue_certificate(
            db, user_id=user_id, course_id=course_id
        )
    except Exception:  # noqa: BLE001
        # Sertifikat berib bo'lmasa, kurs tugatilganligi ham bekor qilinmasin —
        # admin keyinroq qo'lda issue qiladi
        pass

    # Phase 11e — gamification event
    from app.modules.gamification import service as gamif_service

    try:
        await gamif_service.award_event(
            db,
            user_id=user_id,
            event_type="course.completed",
            context={"course_id": course_id},
            dedupe_key=f"course.completed:{user_id}:{course_id}",
        )
    except Exception:  # noqa: BLE001
        pass


async def list_my_courses(
    db: AsyncSession, *, user_id: int
) -> list[tuple[Course, Enrollment]]:
    stmt = (
        select(Course, Enrollment)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .where(
            Enrollment.user_id == user_id,
            Course.deleted_at.is_(None),
        )
        .options(selectinload(Course.modules))
        .order_by(desc(Enrollment.enrolled_at))
    )
    return list((await db.execute(stmt)).all())

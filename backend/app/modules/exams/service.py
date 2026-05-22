"""Exams service — Phase 6a.

Asosiy mantiq:
    - Exam CRUD (faqat kurs muallifi yoki platform.* perm bilan)
    - Question CRUD (Exam'ga bog'liq) + reorder
    - QuestionOption avtomatik to'liq replace (update'da)
    - Publish/archive workflow (Exam.status: draft → published → archived)
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.tenant import get_xiu_org_id
from app.modules.courses.models import Course, Enrollment, Lesson
from app.modules.exams.models import Exam, Question, QuestionOption
from app.modules.exams.schemas import (
    ExamCreateRequest,
    ExamUpdateRequest,
    QuestionCreate,
    QuestionUpdate,
)


def _now() -> datetime:
    return datetime.now(UTC)


# ============================================================================
# Exam
# ============================================================================


async def list_exams(
    db: AsyncSession,
    *,
    course_id: int | None = None,
    lesson_id: int | None = None,
    type: str | None = None,
    status: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Exam], int]:
    stmt = select(Exam).where(Exam.deleted_at.is_(None))
    if course_id is not None:
        stmt = stmt.where(Exam.course_id == course_id)
    if lesson_id is not None:
        stmt = stmt.where(Exam.lesson_id == lesson_id)
    if type:
        stmt = stmt.where(Exam.type == type)
    if status:
        stmt = stmt.where(Exam.status == status)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(Exam.title.ilike(like))

    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()

    stmt = (
        stmt.order_by(Exam.created_at.desc())
        .options(selectinload(Exam.questions))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await db.execute(stmt)).scalars().all()
    return list(items), int(total)


async def list_exams_for_student(
    db: AsyncSession,
    user_id: int,
    *,
    course_id: int | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Exam], int]:
    """Talaba uchun: faqat yozilgan kurslardagi `published` imtihonlar."""
    enrolled = select(Enrollment.course_id).where(Enrollment.user_id == user_id)
    stmt = select(Exam).where(
        Exam.deleted_at.is_(None),
        Exam.status == "published",
        Exam.course_id.in_(enrolled),
    )
    if course_id is not None:
        stmt = stmt.where(Exam.course_id == course_id)

    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()

    stmt = (
        stmt.order_by(Exam.available_from.desc().nullslast(), Exam.created_at.desc())
        .options(selectinload(Exam.questions))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await db.execute(stmt)).scalars().all()
    return list(items), int(total)


async def get_exam(db: AsyncSession, exam_id: int) -> Exam:
    stmt = (
        select(Exam)
        .where(Exam.id == exam_id, Exam.deleted_at.is_(None))
        .options(selectinload(Exam.questions).selectinload(Question.options))
    )
    exam = (await db.execute(stmt)).scalar_one_or_none()
    if exam is None:
        raise NotFoundError("Imtihon topilmadi")
    return exam


async def get_exam_with_stats(
    db: AsyncSession, exam_id: int
) -> tuple[Exam, int, Decimal]:
    """Exam + total_questions + total_points qaytaradi."""
    exam = await get_exam(db, exam_id)
    total_questions = len(exam.questions)
    total_points = sum((q.points for q in exam.questions), Decimal("0"))
    return exam, total_questions, total_points


async def create_exam(
    db: AsyncSession, payload: ExamCreateRequest, *, created_by: int
) -> Exam:
    # Course mavjudligini tekshirish
    course = await db.get(Course, payload.course_id)
    if course is None:
        raise NotFoundError("Kurs topilmadi")

    # Lesson agar berilgan bo'lsa, kursga bog'liqligini tekshirish
    if payload.lesson_id is not None:
        lesson = await db.get(Lesson, payload.lesson_id)
        if lesson is None:
            raise NotFoundError("Dars topilmadi")
        # Lesson → Module → Course chain
        from app.modules.courses.models import Module
        module = await db.get(Module, lesson.module_id)
        if module is None or module.course_id != payload.course_id:
            raise ValidationError("Dars boshqa kursga tegishli")

    # Available_from < available_until
    if (
        payload.available_from
        and payload.available_until
        and payload.available_from >= payload.available_until
    ):
        raise ValidationError(
            "Boshlanish vaqti tugash vaqtidan oldin bo'lishi kerak"
        )

    exam = Exam(
        course_id=payload.course_id,
        lesson_id=payload.lesson_id,
        organization_id=await get_xiu_org_id(db),
        title=payload.title,
        description=payload.description,
        type=payload.type,
        status="draft",
        duration_minutes=payload.duration_minutes,
        max_attempts=payload.max_attempts,
        passing_score=payload.passing_score,
        shuffle_questions=payload.shuffle_questions,
        shuffle_options=payload.shuffle_options,
        show_correct_answers=payload.show_correct_answers,
        question_count=payload.question_count,
        proctoring_enabled=payload.proctoring_enabled,
        require_face_id=payload.require_face_id,
        require_screen_share=payload.require_screen_share,
        allow_tab_switch=payload.allow_tab_switch,
        max_face_loss_seconds=payload.max_face_loss_seconds,
        available_from=payload.available_from,
        available_until=payload.available_until,
        created_by=created_by,
    )
    db.add(exam)
    await db.flush()
    return exam


async def update_exam(
    db: AsyncSession, exam_id: int, payload: ExamUpdateRequest
) -> Exam:
    exam = await get_exam(db, exam_id)
    if exam.status == "archived":
        raise ConflictError("Arxivlangan imtihon tahrirlanmaydi")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(exam, key, value)

    if (
        exam.available_from
        and exam.available_until
        and exam.available_from >= exam.available_until
    ):
        raise ValidationError(
            "Boshlanish vaqti tugash vaqtidan oldin bo'lishi kerak"
        )

    await db.flush()
    return exam


async def delete_exam(db: AsyncSession, exam_id: int) -> None:
    exam = await get_exam(db, exam_id)
    if exam.status == "published":
        raise ConflictError(
            "Publish qilingan imtihonni o'chirib bo'lmaydi. Avval archive qiling."
        )
    exam.deleted_at = _now()
    await db.flush()


async def publish_exam(db: AsyncSession, exam_id: int) -> Exam:
    exam = await get_exam(db, exam_id)
    if exam.status == "published":
        return exam
    if exam.status == "archived":
        raise ConflictError("Arxivlangan imtihonni qayta publish qilib bo'lmaydi")
    # Validation: kamida 1 savol bo'lishi shart
    if not exam.questions:
        raise ValidationError("Imtihonda kamida bitta savol bo'lishi shart")
    exam.status = "published"
    await db.flush()
    # Phase 7d — notify enrolled students
    try:
        from app.modules.notifications.service import notify_exam_published
        await notify_exam_published(
            db, exam_id=exam.id, exam_title=exam.title, course_id=exam.course_id
        )
    except Exception:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).exception(
            "notify_exam_published.failed exam=%s", exam_id
        )
    return exam


async def archive_exam(db: AsyncSession, exam_id: int) -> Exam:
    exam = await get_exam(db, exam_id)
    if exam.status == "archived":
        return exam
    exam.status = "archived"
    exam.closed_at = _now()
    await db.flush()
    # DAK imtihonlari avtomatik HEMIS sync (stub)
    if exam.type == "dak":
        from app.modules.exams.hemis_sync import send_exam_grades  # avoid cyclic
        try:
            await send_exam_grades(db, exam_id)
        except Exception:  # noqa: BLE001 — log only, archive muvaffaqiyatli o'tdi
            import logging
            logging.getLogger(__name__).exception(
                "hemis_sync.auto_failed exam=%s", exam_id
            )
    return exam


# ============================================================================
# Question
# ============================================================================


def _validate_question_payload(q: QuestionCreate | QuestionUpdate) -> None:
    """Savol turiga qarab validation."""
    qtype = q.type
    if qtype is None:
        return
    if qtype in ("single_choice", "multiple_choice", "true_false"):
        options = q.options if hasattr(q, "options") else None
        if options is not None:
            if len(options) < 2:
                raise ValidationError(
                    f"{qtype} savolida kamida 2 ta variant bo'lishi shart"
                )
            correct_count = sum(1 for o in options if o.is_correct)
            if qtype == "single_choice" and correct_count != 1:
                raise ValidationError(
                    "Single choice savolida aniq bitta to'g'ri variant bo'lishi shart"
                )
            if qtype == "multiple_choice" and correct_count < 1:
                raise ValidationError(
                    "Multiple choice savolida kamida bitta to'g'ri variant bo'lishi shart"
                )
            if qtype == "true_false" and len(options) != 2:
                raise ValidationError("True/false savolida aniq 2 ta variant bo'lishi shart")
    elif qtype == "short_text":
        if q.correct_text is None or not q.correct_text.strip():
            raise ValidationError(
                "Short text savolida to'g'ri javob (correct_text) ko'rsatilishi shart"
            )


async def list_questions(db: AsyncSession, exam_id: int) -> list[Question]:
    stmt = (
        select(Question)
        .where(Question.exam_id == exam_id)
        .options(selectinload(Question.options))
        .order_by(Question.order_index)
    )
    return list((await db.execute(stmt)).scalars().all())


async def get_question(db: AsyncSession, question_id: int) -> Question:
    stmt = (
        select(Question)
        .where(Question.id == question_id)
        .options(selectinload(Question.options))
    )
    q = (await db.execute(stmt)).scalar_one_or_none()
    if q is None:
        raise NotFoundError("Savol topilmadi")
    return q


async def create_question(
    db: AsyncSession, exam_id: int, payload: QuestionCreate
) -> Question:
    exam = await get_exam(db, exam_id)
    if exam.status == "published":
        raise ConflictError(
            "Publish qilingan imtihonga savol qo'shish mumkin emas. Avval archive qiling."
        )

    _validate_question_payload(payload)

    question = Question(
        exam_id=exam_id,
        order_index=payload.order_index,
        type=payload.type,
        title=payload.title,
        explanation=payload.explanation,
        points=payload.points,
        required=payload.required,
        code_language=payload.code_language,
        code_initial=payload.code_initial,
        max_file_size_mb=payload.max_file_size_mb,
        allowed_file_types=payload.allowed_file_types,
        exact_match=payload.exact_match,
        case_sensitive=payload.case_sensitive,
        correct_text=payload.correct_text,
        alternative_answers=payload.alternative_answers,
    )
    db.add(question)
    await db.flush()

    # Options
    for opt in payload.options:
        db.add(
            QuestionOption(
                question_id=question.id,
                order_index=opt.order_index,
                text=opt.text,
                is_correct=opt.is_correct,
                explanation=opt.explanation,
            )
        )
    await db.flush()
    # Re-fetch with options loaded
    return await get_question(db, question.id)


async def update_question(
    db: AsyncSession, question_id: int, payload: QuestionUpdate
) -> Question:
    question = await get_question(db, question_id)
    exam = await db.get(Exam, question.exam_id)
    if exam and exam.status == "published":
        raise ConflictError(
            "Publish qilingan imtihondagi savolni tahrirlab bo'lmaydi"
        )

    _validate_question_payload(payload)

    data = payload.model_dump(exclude_unset=True)
    options_data = data.pop("options", None)

    for key, value in data.items():
        setattr(question, key, value)

    # Options to'liq almashtirish (agar berilgan bo'lsa)
    if options_data is not None:
        # Eski variantlarni o'chirish
        for old_opt in list(question.options):
            await db.delete(old_opt)
        await db.flush()
        # Yangilarini qo'shish
        for idx, opt_dict in enumerate(options_data):
            db.add(
                QuestionOption(
                    question_id=question.id,
                    order_index=opt_dict.get("order_index", idx),
                    text=opt_dict["text"],
                    is_correct=opt_dict.get("is_correct", False),
                    explanation=opt_dict.get("explanation"),
                )
            )

    await db.flush()
    return await get_question(db, question_id)


async def delete_question(db: AsyncSession, question_id: int) -> None:
    question = await get_question(db, question_id)
    exam = await db.get(Exam, question.exam_id)
    if exam and exam.status == "published":
        raise ConflictError(
            "Publish qilingan imtihondan savolni o'chirib bo'lmaydi"
        )
    await db.delete(question)
    await db.flush()


async def reorder_questions(
    db: AsyncSession, exam_id: int, ids: list[int]
) -> list[Question]:
    """Berilgan id ketma-ketligi bo'yicha order_index'larni qayta yozish."""
    exam = await get_exam(db, exam_id)
    if exam.status == "published":
        raise ConflictError(
            "Publish qilingan imtihonda savol tartibini o'zgartirib bo'lmaydi"
        )

    # Barcha id'lar shu exam'ga tegishliligini tasdiqlash
    current_ids = {q.id for q in exam.questions}
    if set(ids) != current_ids:
        raise ValidationError("Berilgan id'lar imtihon savollariga mos kelmaydi")

    for idx, qid in enumerate(ids):
        question = await db.get(Question, qid)
        if question is not None:
            question.order_index = idx
    await db.flush()
    return await list_questions(db, exam_id)

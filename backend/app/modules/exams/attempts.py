"""Attempt service — Phase 6b.

Talaba ExamAttempt yaratish, javob saqlash, submit, natija olish,
hamda pedagog manual grading va attempt invalidation logikasi.

Lazy auto-submit: har gal `_load_attempt` chaqirilganda `deadline_at < now` va
`status == 'in_progress'` bo'lsa, attempt avto-submit qilinadi. Bu Celery
infrasiz ham talabaning natijasi to'g'ri ko'rinishini ta'minlaydi.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.modules.exams.grading import grade_attempt_answers
from app.modules.exams.models import Answer, Exam, ExamAttempt, Question


def _now() -> datetime:
    return datetime.now(UTC)


async def _get_exam_for_attempt(db: AsyncSession, exam_id: int) -> Exam:
    stmt = (
        select(Exam)
        .where(Exam.id == exam_id, Exam.deleted_at.is_(None))
        .options(selectinload(Exam.questions).selectinload(Question.options))
    )
    exam = (await db.execute(stmt)).scalar_one_or_none()
    if exam is None:
        raise NotFoundError("Imtihon topilmadi")
    return exam


async def _load_attempt(
    db: AsyncSession, attempt_id: int, *, with_answers: bool = True
) -> ExamAttempt:
    stmt = select(ExamAttempt).where(ExamAttempt.id == attempt_id)
    if with_answers:
        stmt = stmt.options(selectinload(ExamAttempt.answers))
    attempt = (await db.execute(stmt)).scalar_one_or_none()
    if attempt is None:
        raise NotFoundError("Urinish topilmadi")

    # Lazy auto-submit: vaqt o'tib ketgan bo'lsa
    if attempt.status == "in_progress" and attempt.deadline_at <= _now():
        await _finalize_attempt(db, attempt, status="auto_submitted")

    return attempt


def _check_owner(attempt: ExamAttempt, user_id: int) -> None:
    if attempt.user_id != user_id:
        raise ForbiddenError("Bu urinish sizga tegishli emas")


async def start_attempt(db: AsyncSession, exam_id: int, user_id: int) -> ExamAttempt:
    exam = await _get_exam_for_attempt(db, exam_id)

    if exam.status != "published":
        raise ConflictError("Faqat publish qilingan imtihonni boshlash mumkin")

    now = _now()
    if exam.available_from and now < exam.available_from:
        raise ConflictError("Imtihon hali boshlanmadi")
    if exam.available_until and now > exam.available_until:
        raise ConflictError("Imtihon vaqti tugagan")

    # Mavjud in_progress urinish bo'lsa, uni qaytaramiz (kontinuatsiya)
    existing_in_progress = (
        await db.execute(
            select(ExamAttempt).where(
                ExamAttempt.exam_id == exam_id,
                ExamAttempt.user_id == user_id,
                ExamAttempt.status == "in_progress",
            )
        )
    ).scalar_one_or_none()
    if existing_in_progress is not None:
        # Vaqti tugagan bo'lsa, finalize qilamiz va yangi yaratamiz
        if existing_in_progress.deadline_at <= now:
            await _finalize_attempt(db, existing_in_progress, status="auto_submitted")
        else:
            return existing_in_progress

    # Attempt soni cheklovi
    count = (
        await db.execute(
            select(func.count(ExamAttempt.id)).where(
                ExamAttempt.exam_id == exam_id,
                ExamAttempt.user_id == user_id,
                ExamAttempt.status.in_(
                    ("submitted", "auto_submitted", "graded", "in_progress")
                ),
            )
        )
    ).scalar_one()
    if count >= exam.max_attempts:
        raise ConflictError(
            f"Urinishlar soni cheklovi ({exam.max_attempts}) dan oshib ketdi"
        )

    if not exam.questions:
        raise ValidationError("Imtihonda savollar yo'q")

    # Savollar tartibi: shuffle bo'lsa, randomize
    question_ids = [q.id for q in exam.questions]
    if exam.shuffle_questions:
        random.shuffle(question_ids)
    if exam.question_count and exam.question_count < len(question_ids):
        question_ids = question_ids[: exam.question_count]

    # Variant tartibi: shuffle bo'lsa, har savol uchun
    option_order: dict[str, list[int]] = {}
    if exam.shuffle_options:
        for q in exam.questions:
            if q.id in question_ids and q.options:
                opt_ids = [o.id for o in q.options]
                random.shuffle(opt_ids)
                option_order[str(q.id)] = opt_ids

    deadline = now + timedelta(minutes=exam.duration_minutes)
    max_score = sum(
        (q.points for q in exam.questions if q.id in question_ids), Decimal("0")
    )

    attempt = ExamAttempt(
        exam_id=exam_id,
        user_id=user_id,
        attempt_number=count + 1,
        status="in_progress",
        started_at=now,
        deadline_at=deadline,
        question_order=question_ids,
        option_order=option_order or None,
        max_score=max_score,
    )
    db.add(attempt)
    await db.flush()
    return attempt


async def get_attempt(
    db: AsyncSession, attempt_id: int, user_id: int | None = None
) -> ExamAttempt:
    attempt = await _load_attempt(db, attempt_id)
    if user_id is not None:
        _check_owner(attempt, user_id)
    return attempt


async def get_take_view(
    db: AsyncSession, attempt_id: int, user_id: int
) -> tuple[ExamAttempt, Exam, list[Question], list[Answer]]:
    """Talaba imtihon yechish ekrani uchun: attempt + tartibli savollar + saqlangan javoblar."""
    attempt = await _load_attempt(db, attempt_id)
    _check_owner(attempt, user_id)

    if attempt.status not in ("in_progress", "submitted", "auto_submitted", "graded"):
        raise ConflictError("Bu urinishni ko'rib bo'lmaydi")

    exam = await _get_exam_for_attempt(db, attempt.exam_id)

    # Savollar tartibini attempt.question_order bo'yicha qaytaramiz
    by_id = {q.id: q for q in exam.questions}
    ordered_questions = [by_id[qid] for qid in (attempt.question_order or []) if qid in by_id]

    # option_order ham qo'llaniladi (Question.options ni reorder qilamiz)
    if attempt.option_order:
        for q in ordered_questions:
            order = attempt.option_order.get(str(q.id))
            if order:
                opt_by_id = {o.id: o for o in q.options}
                q.options = [opt_by_id[oid] for oid in order if oid in opt_by_id]

    return attempt, exam, ordered_questions, list(attempt.answers)


async def save_answer(
    db: AsyncSession, attempt_id: int, user_id: int, payload
) -> Answer:
    """payload: AnswerSubmit. Mavjud bo'lsa update, bo'lmasa insert."""
    attempt = await _load_attempt(db, attempt_id)
    _check_owner(attempt, user_id)
    if attempt.status != "in_progress":
        raise ConflictError("Bu urinish allaqachon yopilgan")
    if attempt.deadline_at <= _now():
        raise ConflictError("Vaqt tugagan")

    # Savol shu attemptga tegishliligini tekshirish
    if payload.question_id not in (attempt.question_order or []):
        raise ValidationError("Bu savol urinishga kirmaydi")

    existing = next(
        (a for a in attempt.answers if a.question_id == payload.question_id), None
    )
    if existing is None:
        existing = Answer(
            attempt_id=attempt_id,
            question_id=payload.question_id,
        )
        db.add(existing)

    existing.selected_option_ids = payload.selected_option_ids
    existing.text_answer = payload.text_answer
    existing.code_answer = payload.code_answer
    existing.file_url = payload.file_url
    existing.file_size_bytes = payload.file_size_bytes

    await db.flush()
    return existing


async def submit_attempt(
    db: AsyncSession, attempt_id: int, user_id: int
) -> ExamAttempt:
    attempt = await _load_attempt(db, attempt_id)
    _check_owner(attempt, user_id)
    if attempt.status != "in_progress":
        # Allaqachon yopilgan — idempotent qaytamiz
        return attempt
    return await _finalize_attempt(db, attempt, status="submitted")


async def _finalize_attempt(
    db: AsyncSession, attempt: ExamAttempt, *, status: str
) -> ExamAttempt:
    """Submit yoki auto-submit jarayoni: javoblarni baholash + skorlash."""
    exam = await _get_exam_for_attempt(db, attempt.exam_id)
    by_qid = {q.id: q for q in exam.questions}

    # Javobsiz savollar uchun placeholder Answer yaratish
    answered_qids = {a.question_id for a in attempt.answers}
    for qid in attempt.question_order or []:
        if qid not in answered_qids and qid in by_qid:
            empty = Answer(
                attempt_id=attempt.id,
                question_id=qid,
                points_max=by_qid[qid].points,
            )
            db.add(empty)
            attempt.answers.append(empty)

    # Auto-grade
    grade_attempt_answers(list(attempt.answers), [by_qid[qid] for qid in (attempt.question_order or []) if qid in by_qid])

    # Phase 9d — code question auto-grade against test cases
    from app.modules.exams.code_grading import grade_code_answer
    for ans in attempt.answers:
        q = by_qid.get(ans.question_id)
        if q is None or q.type != "code":
            continue
        try:
            points, _results = await grade_code_answer(db, ans, q)
            if points > Decimal("0"):
                ans.points_earned = points
                ans.points_max = q.points
                # Test case'lar mavjud bo'lsa, auto-graded deb belgilaymiz
                ans.auto_correct = points >= q.points
            # Test case yo'q bo'lsa, auto_correct None qoladi (manual)
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                "code_grading.failed attempt=%s q=%s", attempt.id, q.id
            )

    # Phase 9e — plagiarism check (best-effort)
    try:
        from app.modules.exams.plagiarism import check_attempt_plagiarism
        await check_attempt_plagiarism(db, attempt.id)
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            "plagiarism_check.failed attempt=%s", attempt.id
        )

    # Phase 9f — smart anomaly scoring (best-effort)
    try:
        from app.modules.exams.anomaly import apply_smart_score
        await apply_smart_score(db, attempt.id)
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            "smart_score.failed attempt=%s", attempt.id
        )

    auto_total = sum(
        (a.points_earned for a in attempt.answers if a.auto_correct is not None),
        Decimal("0"),
    )
    has_manual_pending = any(
        a.auto_correct is None
        and by_qid.get(a.question_id)
        and by_qid[a.question_id].type in ("essay", "code", "file_upload")
        for a in attempt.answers
    )

    attempt.auto_score = auto_total
    attempt.manual_score = None if has_manual_pending else Decimal("0")
    attempt.total_score = auto_total  # manual qo'shilganda yangilanadi
    if attempt.max_score and attempt.max_score > 0:
        attempt.percentage = (
            attempt.total_score / attempt.max_score * Decimal("100")
        ).quantize(Decimal("0.01"))
    else:
        attempt.percentage = Decimal("0")
    attempt.passed = bool(
        attempt.percentage is not None and attempt.percentage >= exam.passing_score
    )
    attempt.submitted_at = _now()
    attempt.status = status
    attempt.time_spent_seconds = int(
        (attempt.submitted_at - attempt.started_at).total_seconds()
    )

    await db.flush()

    # Phase 11e — gamification
    if attempt.passed:
        from app.modules.gamification import service as gamif_service

        try:
            await gamif_service.award_event(
                db,
                user_id=attempt.user_id,
                event_type="exam.passed",
                context={"exam_id": attempt.exam_id, "attempt_id": attempt.id},
                dedupe_key=f"exam.passed:{attempt.user_id}:{attempt.id}",
            )
            if (
                attempt.percentage is not None
                and attempt.percentage >= Decimal("100")
            ):
                await gamif_service.award_event(
                    db,
                    user_id=attempt.user_id,
                    event_type="exam.perfect",
                    context={"exam_id": attempt.exam_id, "attempt_id": attempt.id},
                    dedupe_key=f"exam.perfect:{attempt.user_id}:{attempt.id}",
                )
        except Exception:  # noqa: BLE001
            pass

    return attempt


async def get_result(
    db: AsyncSession, attempt_id: int, user_id: int
) -> tuple[ExamAttempt, bool]:
    """Talaba natijasi. `show_correct_answers` bayrog'ini ham qaytaradi."""
    attempt = await _load_attempt(db, attempt_id)
    _check_owner(attempt, user_id)
    if attempt.status == "in_progress":
        raise ConflictError("Natija hali tayyor emas — submit qiling")
    exam = await _get_exam_for_attempt(db, attempt.exam_id)
    return attempt, bool(exam.show_correct_answers)


async def list_user_attempts(
    db: AsyncSession, exam_id: int, user_id: int
) -> list[ExamAttempt]:
    stmt = (
        select(ExamAttempt)
        .where(ExamAttempt.exam_id == exam_id, ExamAttempt.user_id == user_id)
        .order_by(ExamAttempt.attempt_number.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def list_exam_attempts(
    db: AsyncSession,
    exam_id: int,
    *,
    user_id: int | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[ExamAttempt], int]:
    stmt = select(ExamAttempt).where(ExamAttempt.exam_id == exam_id)
    if user_id is not None:
        stmt = stmt.where(ExamAttempt.user_id == user_id)
    if status:
        stmt = stmt.where(ExamAttempt.status == status)

    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()

    stmt = (
        stmt.order_by(ExamAttempt.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await db.execute(stmt)).scalars().all()
    return list(items), int(total)


async def grade_attempt(
    db: AsyncSession,
    attempt_id: int,
    *,
    grader_id: int,
    grades: list,
) -> ExamAttempt:
    """Pedagog manual baholash: essay/code/file_upload uchun ball qo'yadi."""
    attempt = await _load_attempt(db, attempt_id)
    if attempt.status == "in_progress":
        raise ConflictError("Hali submit qilinmagan urinishni baholab bo'lmaydi")
    if attempt.status == "invalidated":
        raise ConflictError("Bekor qilingan urinishni baholab bo'lmaydi")

    exam = await _get_exam_for_attempt(db, attempt.exam_id)
    by_qid = {q.id: q for q in exam.questions}
    answers_by_id = {a.id: a for a in attempt.answers}

    now = _now()
    for g in grades:
        ans = answers_by_id.get(g.answer_id)
        if ans is None or ans.attempt_id != attempt_id:
            raise ValidationError(f"Javob #{g.answer_id} topilmadi")
        q = by_qid.get(ans.question_id)
        if q is None:
            continue
        # Avto-baholanadigan turlarni qo'lda qayta baholashga ruxsat bermaymiz
        if q.type not in ("essay", "code", "file_upload"):
            raise ValidationError(
                f"#{q.type} savoli avto-baholanadi — qo'lda baholash mumkin emas"
            )
        if g.points_earned > q.points:
            raise ValidationError(
                f"Ball savol max balli ({q.points}) dan oshib ketdi"
            )
        ans.points_earned = g.points_earned
        ans.points_max = q.points
        ans.graded_by = grader_id
        ans.graded_at = now
        ans.grader_comment = g.grader_comment
        ans.auto_correct = None  # qo'lda baholangan — auto_correct emas

    # Skorni qayta hisoblash
    auto_total = sum(
        (a.points_earned for a in attempt.answers if a.auto_correct is True),
        Decimal("0"),
    )
    # Multiple choice qisman ham hisobga olinadi (auto_correct=False bo'lsa ham points>0)
    auto_partial = sum(
        (
            a.points_earned
            for a in attempt.answers
            if a.auto_correct is False
            and by_qid.get(a.question_id)
            and by_qid[a.question_id].type == "multiple_choice"
        ),
        Decimal("0"),
    )
    manual_total = sum(
        (
            a.points_earned
            for a in attempt.answers
            if a.graded_by is not None
            and by_qid.get(a.question_id)
            and by_qid[a.question_id].type in ("essay", "code", "file_upload")
        ),
        Decimal("0"),
    )

    attempt.auto_score = auto_total + auto_partial
    attempt.manual_score = manual_total
    attempt.total_score = attempt.auto_score + manual_total
    if attempt.max_score and attempt.max_score > 0:
        attempt.percentage = (
            attempt.total_score / attempt.max_score * Decimal("100")
        ).quantize(Decimal("0.01"))
    attempt.passed = bool(
        attempt.percentage is not None and attempt.percentage >= exam.passing_score
    )

    # Manual gradinglar to'liq tugaganmi? Agar manual savollar barchasi baholangan bo'lsa → 'graded'
    manual_questions = [
        a
        for a in attempt.answers
        if by_qid.get(a.question_id)
        and by_qid[a.question_id].type in ("essay", "code", "file_upload")
    ]
    just_graded = False
    if manual_questions and all(a.graded_by is not None for a in manual_questions):
        attempt.status = "graded"
        just_graded = True

    await db.flush()

    # Phase 7d — talabaga bildirishnoma
    if just_graded:
        try:
            from app.modules.notifications.service import notify_attempt_graded
            await notify_attempt_graded(
                db,
                attempt_id=attempt.id,
                exam_id=attempt.exam_id,
                user_id=attempt.user_id,
                percentage=str(attempt.percentage) if attempt.percentage else "0",
            )
        except Exception:  # noqa: BLE001
            import logging
            logging.getLogger(__name__).exception(
                "notify_attempt_graded.failed attempt=%s", attempt.id
            )
    return attempt


async def invalidate_attempt(
    db: AsyncSession, attempt_id: int, *, reason: str
) -> ExamAttempt:
    attempt = await _load_attempt(db, attempt_id)
    if attempt.status == "invalidated":
        return attempt
    attempt.status = "invalidated"
    attempt.flagged = True
    # reason'ni hozircha grader_comment'lar orqali emas, audit log orqali yozish kerak.
    # Phase 6g'da AuditLog'ga yozamiz.
    await db.flush()
    return attempt


async def auto_submit_expired(db: AsyncSession) -> int:
    """Vaqti tugab, hali in_progress bo'lib turgan barcha urinishlarni avto-submit qilish.

    Cron/Celery beat tomonidan har 1 daqiqada chaqirilishi mo'ljallangan.
    """
    now = _now()
    stmt = (
        select(ExamAttempt)
        .where(
            ExamAttempt.status == "in_progress",
            ExamAttempt.deadline_at <= now,
        )
        .options(selectinload(ExamAttempt.answers))
    )
    expired = list((await db.execute(stmt)).scalars().all())
    for attempt in expired:
        await _finalize_attempt(db, attempt, status="auto_submitted")
    return len(expired)

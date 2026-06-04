"""Talaba gradebook agregati — Phase 13.20.

Har bir enrolled kurs uchun:
    - exam_avg: shu kursdagi barcha imtihonlarining eng yaxshi attempt foizlarining o'rtachasi
    - assignment_avg: shu kursdagi gradedlangan submissionlarning o'rtacha foizi
    - total: weighted average (50/50, weight_percent yo'q bo'lsa)

Backend endpointida `/me/gradebook` chaqiruvi orqali ishlatiladi.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.academic.models import Subject
from app.modules.assignments.models import Assignment, Submission
from app.modules.courses.models import Course, Enrollment
from app.modules.exams.models import Exam, ExamAttempt
from app.modules.users.models import User


def _letter_for(percent: float) -> tuple[str, str]:
    """Foiz bo'yicha harfli baho va variant (success/warning/danger)."""
    if percent >= 86:
        return "A'lo", "success"
    if percent >= 71:
        return "Yaxshi", "success"
    if percent >= 55:
        return "Qoniqarli", "warning"
    return "Qoniqarsiz", "danger"


async def get_my_gradebook(
    db: AsyncSession, *, user_id: int
) -> list[dict]:
    """Talaba uchun kursli gradebook qaytaradi."""

    enrolled = (
        await db.execute(
            select(Course)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .where(Enrollment.user_id == user_id)
        )
    ).scalars().all()
    if not enrolled:
        return []

    # Teacher nomi
    author_ids = [c.primary_author_id for c in enrolled if c.primary_author_id]
    teachers: dict[int, str] = {}
    if author_ids:
        rows = (
            await db.execute(
                select(User.id, User.full_name).where(User.id.in_(author_ids))
            )
        ).all()
        teachers = {uid: name for uid, name in rows}

    # Kreditlar — kurs fani (Subject) orqali
    subject_ids = [c.subject_id for c in enrolled if c.subject_id]
    subject_credits: dict[int, int] = {}
    if subject_ids:
        srows = (
            await db.execute(
                select(Subject.id, Subject.credits).where(Subject.id.in_(subject_ids))
            )
        ).all()
        subject_credits = {sid: int(cr) for sid, cr in srows}

    out: list[dict] = []
    for course in enrolled:
        # Exam attemptlar — har bir exam uchun best percentage
        attempts = (
            await db.execute(
                select(Exam.id, Exam.type, ExamAttempt.percentage)
                .join(ExamAttempt, ExamAttempt.exam_id == Exam.id)
                .where(
                    Exam.course_id == course.id,
                    ExamAttempt.user_id == user_id,
                    ExamAttempt.percentage.isnot(None),
                )
            )
        ).all()
        # Group by exam_id => max percentage
        best_per_exam: dict[int, Decimal] = {}
        type_per_exam: dict[int, str] = {}
        for exam_id, ex_type, pct in attempts:
            if exam_id not in best_per_exam or pct > best_per_exam[exam_id]:
                best_per_exam[exam_id] = pct
                type_per_exam[exam_id] = ex_type

        midterm_scores = [
            float(p) for eid, p in best_per_exam.items()
            if type_per_exam.get(eid) == "midterm"
        ]
        final_scores = [
            float(p) for eid, p in best_per_exam.items()
            if type_per_exam.get(eid) == "final"
        ]
        # quiz va practice imtihonlar — joriy (ongoing) baholashga kiradi
        quiz_scores = [
            float(p) for eid, p in best_per_exam.items()
            if type_per_exam.get(eid) in ("quiz", "practice")
        ]

        midterm_avg = sum(midterm_scores) / len(midterm_scores) if midterm_scores else None
        final_avg = sum(final_scores) / len(final_scores) if final_scores else None

        # Assignment submission'lar — gradedlangan
        sub_rows = (
            await db.execute(
                select(Submission.final_score, Assignment.max_score)
                .join(Assignment, Assignment.id == Submission.assignment_id)
                .where(
                    Assignment.course_id == course.id,
                    Submission.user_id == user_id,
                    Submission.final_score.isnot(None),
                )
            )
        ).all()
        assignment_pcts = [
            float(score) / float(maxs) * 100.0
            for score, maxs in sub_rows
            if maxs and float(maxs) > 0
        ]
        # Joriy (ongoing) baho — topshiriqlar + quiz/practice imtihonlar
        current_components = assignment_pcts + quiz_scores
        current_avg = (
            sum(current_components) / len(current_components)
            if current_components
            else None
        )

        # Total — mavjud komponentlar o'rtachasi (joriy / oraliq / yakuniy)
        components = [
            v for v in (current_avg, midterm_avg, final_avg) if v is not None
        ]
        total = sum(components) / len(components) if components else None
        letter, variant = (
            _letter_for(total) if total is not None else ("—", "warning")
        )

        out.append(
            {
                "course_id": course.id,
                "title": course.title,
                "teacher": teachers.get(course.primary_author_id or 0, "—"),
                "credits": subject_credits.get(course.subject_id or 0, 3),
                "current_avg": (
                    f"{current_avg:.1f}" if current_avg is not None else "—"
                ),
                "midterm": (
                    f"{midterm_avg:.1f}" if midterm_avg is not None else "—"
                ),
                "final": (
                    f"{final_avg:.1f}" if final_avg is not None else "—"
                ),
                "total": (f"{total:.1f}" if total is not None else "—"),
                "grade_letter": letter,
                "grade_number": int(total) if total is not None else 0,
                "grade_variant": variant,
            }
        )

    return out

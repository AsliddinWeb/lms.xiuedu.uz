"""Talaba gradebook agregati — Phase 13.20 / 24 / 25.

Har bir enrolled kurs uchun joriy/oraliq/yakuniy komponentlar va total foiz.
Kreditlar fan (Subject) orqali. Phase 25 — semestr bo'yicha tarix.

Endpointlar:
    GET /me/gradebook          → joriy gradebook (kursli)
    GET /me/gradebook/history  → semestr bo'yicha guruhlangan tarix
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


def _gpa_points(percent: float) -> float:
    """4.0 GPA — harf bandlariga mos (>=86=4, >=71=3, >=55=2, aks holda 0)."""
    if percent >= 86:
        return 4.0
    if percent >= 71:
        return 3.0
    if percent >= 55:
        return 2.0
    return 0.0


async def _compute_course(
    db: AsyncSession, course_id: int, user_id: int
) -> tuple[float | None, float | None, float | None, float | None]:
    """Bitta kurs uchun (current_avg, midterm_avg, final_avg, total) qaytaradi."""
    attempts = (
        await db.execute(
            select(Exam.id, Exam.type, ExamAttempt.percentage)
            .join(ExamAttempt, ExamAttempt.exam_id == Exam.id)
            .where(
                Exam.course_id == course_id,
                ExamAttempt.user_id == user_id,
                ExamAttempt.percentage.isnot(None),
            )
        )
    ).all()
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
    quiz_scores = [
        float(p) for eid, p in best_per_exam.items()
        if type_per_exam.get(eid) in ("quiz", "practice")
    ]

    midterm_avg = sum(midterm_scores) / len(midterm_scores) if midterm_scores else None
    final_avg = sum(final_scores) / len(final_scores) if final_scores else None

    sub_rows = (
        await db.execute(
            select(Submission.final_score, Assignment.max_score)
            .join(Assignment, Assignment.id == Submission.assignment_id)
            .where(
                Assignment.course_id == course_id,
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

    current_components = assignment_pcts + quiz_scores
    current_avg = (
        sum(current_components) / len(current_components)
        if current_components
        else None
    )

    components = [v for v in (current_avg, midterm_avg, final_avg) if v is not None]
    total = sum(components) / len(components) if components else None
    return current_avg, midterm_avg, final_avg, total


async def _subject_credits(db: AsyncSession, courses: list[Course]) -> dict[int, int]:
    subject_ids = [c.subject_id for c in courses if c.subject_id]
    if not subject_ids:
        return {}
    srows = (
        await db.execute(
            select(Subject.id, Subject.credits).where(Subject.id.in_(subject_ids))
        )
    ).all()
    return {sid: int(cr) for sid, cr in srows}


async def get_my_gradebook(db: AsyncSession, *, user_id: int) -> list[dict]:
    """Talaba uchun kursli (joriy) gradebook qaytaradi."""
    enrolled = (
        await db.execute(
            select(Course)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .where(Enrollment.user_id == user_id)
        )
    ).scalars().all()
    if not enrolled:
        return []

    author_ids = [c.primary_author_id for c in enrolled if c.primary_author_id]
    teachers: dict[int, str] = {}
    if author_ids:
        rows = (
            await db.execute(
                select(User.id, User.full_name).where(User.id.in_(author_ids))
            )
        ).all()
        teachers = {uid: name for uid, name in rows}

    credits = await _subject_credits(db, list(enrolled))

    out: list[dict] = []
    for course in enrolled:
        current_avg, midterm_avg, final_avg, total = await _compute_course(
            db, course.id, user_id
        )
        letter, variant = (
            _letter_for(total) if total is not None else ("—", "warning")
        )
        out.append(
            {
                "course_id": course.id,
                "title": course.title,
                "teacher": teachers.get(course.primary_author_id or 0, "—"),
                "credits": credits.get(course.subject_id or 0, 3),
                "current_avg": f"{current_avg:.1f}" if current_avg is not None else "—",
                "midterm": f"{midterm_avg:.1f}" if midterm_avg is not None else "—",
                "final": f"{final_avg:.1f}" if final_avg is not None else "—",
                "total": f"{total:.1f}" if total is not None else "—",
                "grade_letter": letter,
                "grade_number": int(total) if total is not None else 0,
                "grade_variant": variant,
            }
        )
    return out


async def get_my_gradebook_history(db: AsyncSession, *, user_id: int) -> list[dict]:
    """Semestr bo'yicha guruhlangan baho tarixi (eng yangi semestr birinchi).

    Har kurs bahosi: avval jonli hisoblanadi; agar hech narsa baholanmagan bo'lsa
    (o'tgan semestr kurslari) — `enrollment.final_grade` ishlatiladi.
    """
    rows = (
        await db.execute(
            select(Enrollment, Course)
            .join(Course, Course.id == Enrollment.course_id)
            .where(Enrollment.user_id == user_id)
        )
    ).all()
    if not rows:
        return []

    credits = await _subject_credits(db, [c for _, c in rows])

    groups: dict[tuple[str, str], dict] = {}
    for enr, course in rows:
        ay = enr.academic_year or "—"
        sem = enr.semester or "—"
        _, _, _, total = await _compute_course(db, course.id, user_id)
        if total is None and enr.final_grade is not None:
            total = float(enr.final_grade)
        letter, variant = _letter_for(total) if total is not None else ("—", "warning")
        g = groups.setdefault(
            (ay, sem),
            {"academic_year": ay, "semester": sem, "courses": [], "_at": enr.enrolled_at},
        )
        if enr.enrolled_at and enr.enrolled_at > g["_at"]:
            g["_at"] = enr.enrolled_at
        g["courses"].append(
            {
                "course_id": course.id,
                "title": course.title,
                "credits": credits.get(course.subject_id or 0, 3),
                "grade_number": int(total) if total is not None else 0,
                "grade_letter": letter,
                "grade_variant": variant,
            }
        )

    out: list[dict] = []
    for g in groups.values():
        graded = [c for c in g["courses"] if c["grade_number"] > 0]
        cr = sum(c["credits"] for c in graded)
        gpa = (
            round(sum(_gpa_points(c["grade_number"]) * c["credits"] for c in graded) / cr, 2)
            if cr
            else None
        )
        avg = (
            round(sum(c["grade_number"] * c["credits"] for c in graded) / cr, 1)
            if cr
            else None
        )
        out.append(
            {
                "academic_year": g["academic_year"],
                "semester": g["semester"],
                "courses": g["courses"],
                "gpa": gpa,
                "avg": avg,
                "total_credits": sum(c["credits"] for c in g["courses"]),
                "_at": g["_at"],
            }
        )
    out.sort(key=lambda x: x["_at"], reverse=True)
    for g in out:
        g.pop("_at", None)
    return out

"""Exam reports module — Phase 6g.

Admin/dean uchun statistik hisobotlar:
    - Jami imtihonlar, urinishlar, o'rtacha ball, pass rate
    - Per-exam breakdown (kurs, type, urinishlar, avg score, pass rate, flagged count)
    - CSV eksport

Filter parametrlari: course_id, type, date_from, date_to.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.courses.models import Course
from app.modules.exams.models import Exam, ExamAttempt


async def summary(
    db: AsyncSession,
    *,
    course_id: int | None = None,
    type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict:
    """4 top-level stat + per-exam ro'yxatini qaytaradi.

    Faqat `submitted`, `auto_submitted`, `graded` urinishlar hisobga olinadi
    (in_progress va invalidated bo'lganlar statistikaga kirmaydi).
    """
    valid_statuses = ("submitted", "auto_submitted", "graded")

    # Exam filtri
    exam_filters = [Exam.deleted_at.is_(None)]
    if course_id is not None:
        exam_filters.append(Exam.course_id == course_id)
    if type:
        exam_filters.append(Exam.type == type)

    # Attempt filtri (date)
    attempt_filters = [ExamAttempt.status.in_(valid_statuses)]
    if date_from is not None:
        attempt_filters.append(ExamAttempt.submitted_at >= date_from)
    if date_to is not None:
        attempt_filters.append(ExamAttempt.submitted_at <= date_to)

    # Top-level statlar
    total_exams_q = select(func.count(Exam.id)).where(and_(*exam_filters))
    total_exams = (await db.execute(total_exams_q)).scalar_one()

    total_attempts_q = (
        select(func.count(ExamAttempt.id))
        .join(Exam, Exam.id == ExamAttempt.exam_id)
        .where(and_(*exam_filters, *attempt_filters))
    )
    total_attempts = (await db.execute(total_attempts_q)).scalar_one()

    avg_score_q = (
        select(func.avg(ExamAttempt.percentage))
        .join(Exam, Exam.id == ExamAttempt.exam_id)
        .where(and_(*exam_filters, *attempt_filters))
    )
    avg_score = (await db.execute(avg_score_q)).scalar()

    pass_count_q = (
        select(func.count(ExamAttempt.id))
        .join(Exam, Exam.id == ExamAttempt.exam_id)
        .where(and_(*exam_filters, *attempt_filters, ExamAttempt.passed.is_(True)))
    )
    pass_count = (await db.execute(pass_count_q)).scalar_one()

    pass_rate = (
        float(pass_count) / float(total_attempts) * 100.0 if total_attempts else 0.0
    )

    # Per-exam breakdown
    rows_q = (
        select(
            Exam.id,
            Exam.title,
            Exam.type,
            Exam.status,
            Course.id,
            Course.title,
            func.count(ExamAttempt.id).label("attempts"),
            func.avg(ExamAttempt.percentage).label("avg_pct"),
            func.sum(case((ExamAttempt.passed.is_(True), 1), else_=0)).label(
                "passed_count"
            ),
            func.sum(case((ExamAttempt.flagged.is_(True), 1), else_=0)).label(
                "flagged_count"
            ),
        )
        .join(Course, Course.id == Exam.course_id)
        .outerjoin(
            ExamAttempt,
            and_(ExamAttempt.exam_id == Exam.id, *attempt_filters),
        )
        .where(and_(*exam_filters))
        .group_by(Exam.id, Course.id)
        .order_by(Exam.created_at.desc())
    )
    rows = (await db.execute(rows_q)).all()

    items = []
    for r in rows:
        n = int(r[6] or 0)
        avg = float(r[7]) if r[7] is not None else 0.0
        passed = int(r[8] or 0)
        flagged = int(r[9] or 0)
        items.append(
            {
                "exam_id": r[0],
                "exam_title": r[1],
                "exam_type": r[2],
                "exam_status": r[3],
                "course_id": r[4],
                "course_title": r[5],
                "attempts": n,
                "avg_percentage": round(avg, 2),
                "passed_count": passed,
                "flagged_count": flagged,
                "pass_rate": (
                    round(passed / n * 100.0, 2) if n else 0.0
                ),
            }
        )

    return {
        "total_exams": int(total_exams),
        "total_attempts": int(total_attempts),
        "avg_percentage": round(float(avg_score), 2) if avg_score is not None else 0.0,
        "pass_rate": round(pass_rate, 2),
        "items": items,
    }


def to_csv(report: dict) -> str:
    """Per-exam ro'yxatini CSV string sifatida qaytaradi."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "exam_id",
            "exam_title",
            "exam_type",
            "course_title",
            "attempts",
            "avg_percentage",
            "passed_count",
            "pass_rate",
            "flagged_count",
        ]
    )
    for row in report["items"]:
        writer.writerow(
            [
                row["exam_id"],
                row["exam_title"],
                row["exam_type"],
                row["course_title"],
                row["attempts"],
                row["avg_percentage"],
                row["passed_count"],
                row["pass_rate"],
                row["flagged_count"],
            ]
        )
    return buf.getvalue()

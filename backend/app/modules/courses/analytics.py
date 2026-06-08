"""Pedagog statistikasi — aggregate analytics (Phase 34).

Bitta chaqiruvda pedagog barcha kurslari bo'yicha ko'rsatkichlar:
KPI'lar, baho/holat taqsimoti, ro'yxat dinamikasi (oylar), imtihon pass-rate,
live sessiyalar. Hammasi `Course.primary_author_id == teacher_id` bo'yicha
filtrlanadi (boshqa pedagog ma'lumotlari ko'rinmaydi).

Cross-module bo'lgani uchun model importlari funksiya ichida (circular oldini olish).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, case, desc, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_teacher_analytics(db: AsyncSession, teacher_id: int) -> dict:
    from app.modules.courses.models import Course, Enrollment

    def _teacher_courses_join(stmt):
        return stmt.join(
            Course,
            and_(
                Course.id == Enrollment.course_id,
                Course.primary_author_id == teacher_id,
                Course.deleted_at.is_(None),
            ),
        )

    # --- Kurslar ---
    crow = (
        await db.execute(
            select(
                func.count(Course.id),
                func.coalesce(
                    func.sum(case((Course.status == "published", 1), else_=0)), 0
                ),
            ).where(
                Course.primary_author_id == teacher_id, Course.deleted_at.is_(None)
            )
        )
    ).one()
    total_courses, published_courses = int(crow[0]), int(crow[1])

    # --- Ro'yxatlar (enrollment) aggregate: holat + baho taqsimoti ---
    agg = (
        await db.execute(
            _teacher_courses_join(
                select(
                    func.count(Enrollment.id),
                    func.count(distinct(Enrollment.user_id)),
                    func.coalesce(
                        func.sum(
                            case((Enrollment.completion_status == "completed", 1), else_=0)
                        ),
                        0,
                    ),
                    func.coalesce(
                        func.sum(
                            case((Enrollment.completion_status == "in_progress", 1), else_=0)
                        ),
                        0,
                    ),
                    func.coalesce(
                        func.sum(
                            case((Enrollment.completion_status == "failed", 1), else_=0)
                        ),
                        0,
                    ),
                    func.coalesce(
                        func.sum(
                            case((Enrollment.completion_status == "dropped", 1), else_=0)
                        ),
                        0,
                    ),
                    func.avg(Enrollment.final_grade),
                    func.coalesce(
                        func.sum(case((Enrollment.final_grade >= 86, 1), else_=0)), 0
                    ),
                    func.coalesce(
                        func.sum(
                            case(
                                (and_(Enrollment.final_grade >= 71, Enrollment.final_grade < 86), 1),
                                else_=0,
                            )
                        ),
                        0,
                    ),
                    func.coalesce(
                        func.sum(
                            case(
                                (and_(Enrollment.final_grade >= 55, Enrollment.final_grade < 71), 1),
                                else_=0,
                            )
                        ),
                        0,
                    ),
                    func.coalesce(
                        func.sum(
                            case(
                                (and_(Enrollment.final_grade.isnot(None), Enrollment.final_grade < 55), 1),
                                else_=0,
                            )
                        ),
                        0,
                    ),
                ).select_from(Enrollment)
            )
        )
    ).one()
    (
        total_enr,
        unique_students,
        completed,
        in_progress,
        failed,
        dropped,
        avg_grade,
        b_exc,
        b_good,
        b_sat,
        b_fail,
    ) = agg

    total_enr = int(total_enr)
    completion_rate = round(int(completed) / total_enr * 100, 1) if total_enr else 0.0

    # --- Ro'yxat dinamikasi (oxirgi 6 oy) ---
    since = datetime.now(UTC) - timedelta(days=185)
    month_expr = func.to_char(func.date_trunc("month", Enrollment.enrolled_at), "YYYY-MM")
    over_time_rows = (
        await db.execute(
            _teacher_courses_join(
                select(month_expr.label("m"), func.count().label("c")).select_from(Enrollment)
            )
            .where(Enrollment.enrolled_at >= since)
            .group_by(month_expr)
            .order_by(month_expr)
        )
    ).all()
    enrollments_over_time = [{"month": m, "count": int(c)} for m, c in over_time_rows]

    # --- Baholash navbati (submitted) ---
    from app.modules.assignments.models import Assignment, Submission

    pending_grading = int(
        (
            await db.execute(
                select(func.count(Submission.id))
                .select_from(Submission)
                .join(Assignment, Assignment.id == Submission.assignment_id)
                .join(
                    Course,
                    and_(
                        Course.id == Assignment.course_id,
                        Course.primary_author_id == teacher_id,
                        Course.deleted_at.is_(None),
                    ),
                )
                .where(Submission.status == "submitted")
            )
        ).scalar_one()
    )

    # --- Imtihon pass-rate ---
    from app.modules.exams.models import Exam, ExamAttempt

    erow = (
        await db.execute(
            select(
                func.coalesce(
                    func.sum(case((ExamAttempt.passed.isnot(None), 1), else_=0)), 0
                ),
                func.coalesce(
                    func.sum(case((ExamAttempt.passed.is_(True), 1), else_=0)), 0
                ),
            )
            .select_from(ExamAttempt)
            .join(Exam, Exam.id == ExamAttempt.exam_id)
            .join(
                Course,
                and_(
                    Course.id == Exam.course_id,
                    Course.primary_author_id == teacher_id,
                    Course.deleted_at.is_(None),
                ),
            )
        )
    ).one()
    exam_attempts, exam_passed = int(erow[0]), int(erow[1])
    exam_pass_rate = (
        round(exam_passed / exam_attempts * 100, 1) if exam_attempts else None
    )

    # --- Per-kurs breakdown (talaba/tugatish/baho) ---
    pc_rows = (
        await db.execute(
            select(
                Course.id,
                Course.title,
                Course.status,
                func.count(Enrollment.id),
                func.coalesce(
                    func.sum(
                        case((Enrollment.completion_status == "completed", 1), else_=0)
                    ),
                    0,
                ),
                func.avg(Enrollment.final_grade),
            )
            .select_from(Course)
            .outerjoin(Enrollment, Enrollment.course_id == Course.id)
            .where(
                Course.primary_author_id == teacher_id, Course.deleted_at.is_(None)
            )
            .group_by(Course.id, Course.title, Course.status)
            .order_by(desc(func.count(Enrollment.id)), Course.title)
        )
    ).all()
    per_course = []
    for cid, title, cstatus, scount, ccount, cavg in pc_rows:
        scount = int(scount)
        per_course.append(
            {
                "course_id": cid,
                "title": title,
                "status": cstatus,
                "student_count": scount,
                "completed_count": int(ccount),
                "completion_rate": round(int(ccount) / scount * 100, 1) if scount else 0.0,
                "avg_grade": float(cavg) if cavg is not None else None,
            }
        )

    # --- Live sessiyalar ---
    from app.modules.live.models import LiveSession

    live_sessions_count = int(
        (
            await db.execute(
                select(func.count(LiveSession.id)).where(
                    LiveSession.host_user_id == teacher_id
                )
            )
        ).scalar_one()
    )

    return {
        "total_courses": total_courses,
        "published_courses": published_courses,
        "total_students": int(unique_students),
        "total_enrollments": total_enr,
        "completion_rate": completion_rate,
        "avg_grade": float(avg_grade) if avg_grade is not None else None,
        "pending_grading": pending_grading,
        "grade_distribution": {
            "excellent": int(b_exc),
            "good": int(b_good),
            "satisfactory": int(b_sat),
            "fail": int(b_fail),
        },
        "completion_breakdown": {
            "in_progress": int(in_progress),
            "completed": int(completed),
            "failed": int(failed),
            "dropped": int(dropped),
        },
        "enrollments_over_time": enrollments_over_time,
        "exam_attempts": exam_attempts,
        "exam_pass_rate": exam_pass_rate,
        "live_sessions_count": live_sessions_count,
        "per_course": per_course,
    }

"""Demo ma'lumotlar seed — to'liq ishlaydigan demo holat.

Bazani realistik demo kontent bilan to'ldiradi: akademik tuzilma, talabalar,
kurslar (modul + dars + kontent), enrollment + progress, topshiriq + topshirilgan
ishlar, live darslar, forum, sertifikat, gamifikatsiya, bildirishnomalar.

Foydalanish:
  docker compose exec backend python -m app.db.seed       # avval rollar + demo userlar
  docker compose exec backend python -m app.db.demo_seed  # keyin demo kontent

Idempotent — qayta ishlatilsa mavjud yozuvlarni o'tkazib yuboradi.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.core.tenant import ensure_xiu_org
from app.db import models as _models  # noqa: F401  # barcha modellarni ro'yxatga olish
from app.modules.academic.models import (
    AcademicCalendar,
    AcademicGroup,
    AcademicSemester,
    Curriculum,
    CurriculumSubject,
    Department,
    Faculty,
    Specialty,
    Subject,
)
from app.modules.assignments.models import (
    Assignment,
    GradeAppeal,
    Rubric,
    Submission,
)
from app.modules.certificates.models import Certificate
from app.modules.communications.models import (
    Conversation,
    ConversationMember,
    ForumPost,
    ForumThread,
    Message,
)
from app.modules.content.models import ContentItem
from app.modules.courses.models import (
    Course,
    CourseReview,
    Enrollment,
    Lesson,
    LessonProgress,
    Module,
)
from app.modules.exams.models import (
    Answer,
    Exam,
    ExamAttempt,
    Question,
    QuestionOption,
)
from app.modules.gamification.models import (
    Badge,
    GamificationEvent,
    UserBadge,
    UserPoints,
)
from app.modules.live.models import LiveAttendance, LiveRecording, LiveSession
from app.modules.notifications.models import Notification
from app.modules.rbac.models import Role, UserRole
from app.modules.users.models import Profile, User

UTC = timezone.utc


def now() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Generic helper
# ---------------------------------------------------------------------------


async def get_or_create(
    db: AsyncSession, model, defaults: dict | None = None, **filters
):
    """Bitta qator: filtrlarga mos topadi yoki yaratadi. (obj, created) qaytaradi."""
    result = await db.execute(select(model).filter_by(**filters))
    obj = result.scalars().first()
    if obj is not None:
        return obj, False
    params = {**filters, **(defaults or {})}
    obj = model(**params)
    db.add(obj)
    await db.flush()
    return obj, True


async def get_user(db: AsyncSession, email: str) -> User | None:
    res = await db.execute(select(User).where(User.email == email))
    return res.scalar_one_or_none()


# ---------------------------------------------------------------------------
# 1. Talabalar (asosiy + qo'shimcha demo guruh)
# ---------------------------------------------------------------------------

EXTRA_STUDENTS = [
    ("talaba2@xiuedu.uz", "Talaba!2026", "Dilnoza Karimova"),
    ("talaba3@xiuedu.uz", "Talaba!2026", "Jasur Rahimov"),
    ("talaba4@xiuedu.uz", "Talaba!2026", "Malika Tosheva"),
    ("talaba5@xiuedu.uz", "Talaba!2026", "Bekzod Aliyev"),
]


async def seed_students(db: AsyncSession, student_role: Role) -> list[User]:
    students: list[User] = []
    for email, password, full_name in EXTRA_STUDENTS:
        user = await get_user(db, email)
        if user is None:
            user = User(
                email=email,
                password_hash=hash_password(password),
                full_name=full_name,
                is_active=True,
                is_verified=True,
            )
            user.profile = Profile()
            db.add(user)
            await db.flush()
            db.add(
                UserRole(user_id=user.id, role_id=student_role.id, scope_type="global")
            )
            await db.flush()
        students.append(user)
    return students


# ---------------------------------------------------------------------------
# 2. Akademik tuzilma
# ---------------------------------------------------------------------------


async def seed_academic(db: AsyncSession, org, dean: User, dep_head: User):
    faculty, _ = await get_or_create(
        db,
        Faculty,
        defaults={"name": "Raqamli texnologiyalar fakulteti", "short_name": "RTF", "dean_id": dean.id},
        organization_id=org.id,
        code="RTF",
    )
    department, _ = await get_or_create(
        db,
        Department,
        defaults={"name": "Kompyuter injiniringi kafedrasi", "head_id": dep_head.id},
        faculty_id=faculty.id,
        code="KI",
    )
    specialty, _ = await get_or_create(
        db,
        Specialty,
        defaults={
            "name": "Kompyuter injiniringi",
            "level": "bachelor",
            "duration_years": 4,
            "education_form": "distance",
            "language": "uz-lat",
            "distance_enabled": True,
            "annual_quota": 120,
        },
        department_id=department.id,
        code="60610100",
    )

    subjects_spec = [
        ("PY101", "Python dasturlash asoslari", 6, 30, 30),
        ("DB201", "Ma'lumotlar bazasi (SQL)", 5, 24, 30),
        ("WEB202", "Web dasturlash: HTML, CSS, JS", 5, 24, 30),
        ("ALG301", "Algoritmlar va ma'lumotlar tuzilmasi", 6, 30, 30),
    ]
    subjects: dict[str, Subject] = {}
    for code, name, credits, lec, prac in subjects_spec:
        subj, _ = await get_or_create(
            db,
            Subject,
            defaults={
                "name": name,
                "credits": credits,
                "lecture_hours": lec,
                "practice_hours": prac,
                "self_study_hours": 60,
                "language": "uz-lat",
            },
            department_id=department.id,
            code=code,
        )
        subjects[code] = subj

    curriculum, created_curr = await get_or_create(
        db,
        Curriculum,
        defaults={
            "name": "Kompyuter injiniringi — 2025 o'quv reja",
            "version": "2025-v1",
            "valid_from": date(2025, 9, 1),
            "based_on": "DTS",
            "total_credits": 240,
            "is_active": True,
        },
        specialty_id=specialty.id,
    )
    if created_curr:
        sem_map = {"PY101": 1, "DB201": 2, "WEB202": 3, "ALG301": 3}
        for code, sem in sem_map.items():
            db.add(
                CurriculumSubject(
                    curriculum_id=curriculum.id,
                    subject_id=subjects[code].id,
                    semester=sem,
                    is_required=True,
                )
            )
        await db.flush()

    await get_or_create(
        db,
        AcademicCalendar,
        defaults={
            "name": "2025-2026 o'quv yili",
            "start_date": date(2025, 9, 1),
            "end_date": date(2026, 6, 30),
            "semesters": [
                {"name": "Kuzgi semestr", "start": "2025-09-01", "end": "2026-01-15"},
                {"name": "Bahorgi semestr", "start": "2026-02-01", "end": "2026-06-30"},
            ],
            "holidays": [
                {"name": "Yangi yil", "date": "2026-01-01"},
                {"name": "Xotira va qadrlash kuni", "date": "2026-05-09"},
            ],
        },
        organization_id=org.id,
        academic_year="2025-2026",
    )

    semester, _ = await get_or_create(
        db,
        AcademicSemester,
        defaults={
            "name": "2025-2026 Bahorgi semestr",
            "code": "2026-spring",
            "education_year_name": "2025-2026",
            "is_current": True,
        },
        hemis_id=20260201,
    )

    group, _ = await get_or_create(
        db,
        AcademicGroup,
        defaults={
            "name": "KI-24-1",
            "education_lang": "uz-lat",
            "faculty_id": faculty.id,
            "specialty_id": specialty.id,
        },
        hemis_id=2024110001,
    )

    return faculty, department, specialty, subjects, group, semester


async def assign_student_fields(
    db: AsyncSession, students: list[User], group: AcademicGroup, org
):
    for s in students:
        s.group_id = group.id
        s.education_form = "distance"
        s.payment_form = "contract"
        s.student_status = "active"
        s.tenant_id = org.id
    await db.flush()


# ---------------------------------------------------------------------------
# 3. Kurslar (modul + dars + kontent)
# ---------------------------------------------------------------------------

COURSES_SPEC = [
    {
        "slug": "python-asoslari",
        "code": "PY101",
        "subject": "PY101",
        "title": "Python dasturlash asoslari",
        "description": "Noldan boshlab Python tilini o'rganamiz: o'zgaruvchilar, shartlar, sikllar, funksiyalar va OOP asoslari.",
        "level": "beginner",
        "duration_weeks": 8,
        "estimated_hours": 40,
        "objectives": ["Python sintaksisini bilish", "Funksiya va modullar bilan ishlash", "OOP asoslarini tushunish"],
        "skills_gained": ["Python", "Algoritmik fikrlash", "Toza kod yozish"],
        "modules": [
            ("Kirish va asosiy sintaksis", [
                ("Python bilan tanishuv", "video", 12),
                ("O'zgaruvchilar va ma'lumot turlari", "text", 15),
                ("Operatorlar va ifodalar", "text", 10),
            ]),
            ("Boshqaruv tuzilmalari", [
                ("Shart operatorlari (if/else)", "video", 14),
                ("Sikllar (for, while)", "video", 16),
            ]),
            ("Funksiyalar va OOP", [
                ("Funksiyalar", "text", 18),
                ("Klass va obyektlar", "video", 20),
            ]),
        ],
    },
    {
        "slug": "sql-malumotlar-bazasi",
        "code": "DB201",
        "subject": "DB201",
        "title": "Ma'lumotlar bazasi (SQL)",
        "description": "Relyatsion ma'lumotlar bazasi, SQL so'rovlari, JOIN, indekslar va normalizatsiya.",
        "level": "intermediate",
        "duration_weeks": 6,
        "estimated_hours": 30,
        "objectives": ["SQL so'rovlarini yozish", "JOIN turlarini bilish", "Bazani normalizatsiya qilish"],
        "skills_gained": ["SQL", "PostgreSQL", "Ma'lumotlar modeli"],
        "modules": [
            ("Relyatsion baza asoslari", [
                ("Ma'lumotlar bazasi nima?", "text", 10),
                ("Jadvallar va kalitlar", "video", 14),
            ]),
            ("SQL so'rovlari", [
                ("SELECT va WHERE", "video", 16),
                ("JOIN turlari", "video", 18),
                ("Agregat funksiyalar", "text", 12),
            ]),
        ],
    },
    {
        "slug": "web-asoslari",
        "code": "WEB202",
        "subject": "WEB202",
        "title": "Web dasturlash: HTML, CSS, JS",
        "description": "Zamonaviy frontend asoslari: semantik HTML, responsive CSS va JavaScript bilan interaktivlik.",
        "level": "beginner",
        "duration_weeks": 7,
        "estimated_hours": 35,
        "objectives": ["Semantik HTML yozish", "Responsive dizayn qilish", "DOM bilan ishlash"],
        "skills_gained": ["HTML", "CSS", "JavaScript"],
        "modules": [
            ("HTML asoslari", [
                ("HTML hujjat tuzilishi", "video", 12),
                ("Semantik teglar", "text", 10),
            ]),
            ("CSS va dizayn", [
                ("Selektorlar va box model", "video", 15),
                ("Flexbox va Grid", "video", 18),
            ]),
            ("JavaScript", [
                ("O'zgaruvchilar va funksiyalar", "text", 14),
                ("DOM manipulyatsiyasi", "video", 20),
            ]),
        ],
    },
    {
        "slug": "algoritmlar",
        "code": "ALG301",
        "subject": "ALG301",
        "title": "Algoritmlar va ma'lumotlar tuzilmasi",
        "description": "Saralash, qidirish algoritmlari, massiv, bog'langan ro'yxat, daraxt va graf tuzilmalari.",
        "level": "advanced",
        "duration_weeks": 8,
        "estimated_hours": 45,
        "objectives": ["Algoritm samaradorligini baholash", "Asosiy tuzilmalarni qo'llash"],
        "skills_gained": ["Algoritmlar", "Big-O", "Problem solving"],
        "modules": [
            ("Murakkablik va saralash", [
                ("Big-O notatsiyasi", "text", 16),
                ("Saralash algoritmlari", "video", 22),
            ]),
            ("Ma'lumotlar tuzilmalari", [
                ("Massiv va ro'yxat", "video", 18),
                ("Daraxt va graf", "video", 24),
            ]),
        ],
    },
    # --- Kashf qilinadigan kurslar (asosiy talaba yozilmagan — katalog uchun) ---
    {
        "slug": "git-github-asoslari",
        "code": "GIT101",
        "subject": "WEB202",
        "title": "Git va GitHub asoslari",
        "description": "Versiyalarni boshqarish: commit, branch, merge, pull request va jamoaviy ishlash.",
        "level": "beginner",
        "type": "open",
        "duration_weeks": 4,
        "estimated_hours": 18,
        "objectives": ["Git bilan ishlash", "Branch va merge", "GitHub'da hamkorlik"],
        "skills_gained": ["Git", "GitHub", "Versiya nazorati"],
        "modules": [
            ("Git asoslari", [
                ("Git nima va nega kerak?", "text", 10),
                ("Commit va tarix", "video", 14),
            ]),
            ("Hamkorlik", [
                ("Branch va merge", "video", 16),
                ("Pull request oqimi", "text", 12),
            ]),
        ],
    },
    {
        "slug": "python-data-analiz",
        "code": "PYDATA1",
        "subject": "PY101",
        "title": "Python bilan ma'lumotlar tahlili",
        "description": "Pandas va NumPy yordamida ma'lumotlarni tozalash, tahlil qilish va vizualizatsiya.",
        "level": "intermediate",
        "type": "micro",
        "duration_weeks": 5,
        "estimated_hours": 25,
        "objectives": ["Pandas DataFrame", "Ma'lumot tozalash", "Vizualizatsiya"],
        "skills_gained": ["Pandas", "NumPy", "Data analysis"],
        "modules": [
            ("Pandas asoslari", [
                ("DataFrame va Series", "video", 18),
                ("Ma'lumot tozalash", "text", 15),
            ]),
            ("Vizualizatsiya", [
                ("Matplotlib bilan grafiklar", "video", 20),
            ]),
        ],
    },
]


async def seed_courses(
    db: AsyncSession, org, teacher: User, subjects: dict[str, Subject]
) -> list[Course]:
    courses: list[Course] = []
    for spec in COURSES_SPEC:
        course = (
            await db.execute(select(Course).where(Course.slug == spec["slug"]))
        ).scalar_one_or_none()
        if course is not None:
            courses.append(course)
            continue

        course = Course(
            code=spec["code"],
            title=spec["title"],
            slug=spec["slug"],
            description=spec["description"],
            subject_id=subjects[spec["subject"]].id,
            organization_id=org.id,
            type=spec.get("type", "academic"),
            level=spec["level"],
            language="uz-lat",
            duration_weeks=spec["duration_weeks"],
            estimated_hours=spec["estimated_hours"],
            objectives=spec["objectives"],
            skills_gained=spec["skills_gained"],
            status="published",
            published_at=now() - timedelta(days=40),
            enrollment_type="self",
            primary_author_id=teacher.id,
        )
        db.add(course)
        await db.flush()

        for m_idx, (m_title, lessons) in enumerate(spec["modules"]):
            module = Module(
                course_id=course.id,
                title=m_title,
                order_index=m_idx,
            )
            db.add(module)
            await db.flush()

            for l_idx, (l_title, ctype, minutes) in enumerate(lessons):
                content = ContentItem(
                    type=ctype,
                    title=l_title,
                    description=f"{l_title} — {course.title} kursi materiali.",
                    subject_id=subjects[spec["subject"]].id,
                    author_id=teacher.id,
                    language="uz-lat",
                    status="published",
                    published_at=now() - timedelta(days=38),
                    duration_seconds=(minutes * 60) if ctype == "video" else None,
                    file_url=(
                        "https://cdn.xiuedu.uz/demo/sample.mp4"
                        if ctype == "video"
                        else None
                    ),
                    content_data=(
                        {
                            "plain": (
                                f"{l_title}\n\n"
                                f"Ushbu darsda \"{l_title}\" mavzusini batafsil ko'rib chiqamiz. "
                                f"Nazariy qism, amaliy misollar va mustaqil mashqlar bilan tanishasiz.\n\n"
                                f"Dars yakunida mavzu bo'yicha qisqa savol-javob va topshiriq beriladi."
                            )
                        }
                        if ctype == "text"
                        else {}
                    ),
                )
                db.add(content)
                await db.flush()

                lesson = Lesson(
                    module_id=module.id,
                    title=l_title,
                    order_index=l_idx,
                    primary_content_id=content.id,
                    estimated_minutes=minutes,
                )
                db.add(lesson)
                await db.flush()

        courses.append(course)
    return courses


async def course_lessons(db: AsyncSession, course: Course) -> list[Lesson]:
    rows = await db.execute(
        select(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .where(Module.course_id == course.id)
        .order_by(Module.order_index, Lesson.order_index)
    )
    return list(rows.scalars().all())


# ---------------------------------------------------------------------------
# 4. Enrollment + progress
# ---------------------------------------------------------------------------


async def enroll(
    db: AsyncSession, course: Course, user: User, *, method="self", status="in_progress"
) -> Enrollment:
    existing = (
        await db.execute(
            select(Enrollment).where(
                Enrollment.course_id == course.id, Enrollment.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    e = Enrollment(
        course_id=course.id,
        user_id=user.id,
        enrollment_method=method,
        completion_status=status,
    )
    db.add(e)
    await db.flush()
    return e


async def set_progress(
    db: AsyncSession, user: User, lessons: list[Lesson], fraction: float
):
    """Birinchi `fraction` ulushdagi darslarni tugatilgan deb belgilaydi."""
    count = max(0, round(len(lessons) * fraction))
    for i, lesson in enumerate(lessons):
        done = i < count
        existing = (
            await db.execute(
                select(LessonProgress).where(
                    LessonProgress.user_id == user.id,
                    LessonProgress.lesson_id == lesson.id,
                )
            )
        ).scalar_one_or_none()
        if existing:
            continue
        lp = LessonProgress(
            user_id=user.id,
            lesson_id=lesson.id,
            started_at=now() - timedelta(days=20 - i),
            completed_at=(now() - timedelta(days=19 - i)) if done else None,
            progress_percent=Decimal("100") if done else Decimal("0"),
            time_spent_seconds=(lesson.estimated_minutes or 10) * 60 if done else 0,
        )
        db.add(lp)
    await db.flush()


# ---------------------------------------------------------------------------
# 5. Topshiriqlar + topshirilgan ishlar
# ---------------------------------------------------------------------------


async def _get_assignment(db: AsyncSession, course_id: int, title: str):
    return (
        await db.execute(
            select(Assignment).where(
                Assignment.course_id == course_id, Assignment.title == title
            )
        )
    ).scalar_one_or_none()


async def seed_assignments(
    db: AsyncSession,
    courses: list[Course],
    teacher: User,
    main_student: User,
):
    # --- (a) Har kursga oddiy fayl topshirig'i; 1-kursda baholangan ish ---
    for idx, course in enumerate(courses[:3]):
        title = f"{course.title} — amaliy topshiriq"
        if await _get_assignment(db, course.id, title):
            continue
        due = now() + timedelta(days=7 - idx * 3)
        assignment = Assignment(
            course_id=course.id,
            title=title,
            description="Kurs mavzusi bo'yicha amaliy ishni bajaring va faylni yuklang.",
            instructions="1. Topshiriqni diqqat bilan o'qing.\n2. Yechimni tayyorlang.\n3. Faylni yuklab, topshiring.",
            type="file",
            available_from=now() - timedelta(days=5),
            due_date=due,
            max_score=Decimal("100"),
            pass_score=Decimal("60"),
            weight_percent=Decimal("20"),
            allowed_file_types=["pdf", "docx", "zip"],
            is_published=True,
            created_by=teacher.id,
        )
        db.add(assignment)
        await db.flush()

        if idx == 0:
            db.add(
                Submission(
                    assignment_id=assignment.id,
                    user_id=main_student.id,
                    attempt_number=1,
                    content="Topshiriq yechimi ilova qilingan faylda.",
                    files=[{"name": "yechim.pdf", "url": "https://cdn.xiuedu.uz/demo/yechim.pdf", "mime": "application/pdf", "size": 102400}],
                    status="graded",
                    score=Decimal("88"),
                    final_score=Decimal("88"),
                    grade_letter="B",
                    feedback="Yaxshi ish! Kod tuzilishi toza, lekin izohlar yetishmaydi.",
                    graded_by=teacher.id,
                    graded_at=now() - timedelta(days=2),
                )
            )
            await db.flush()

    # --- (b) Insho (essay) topshirig'i — talaba yozishi uchun (draft demo) ---
    essay_title = f"{courses[0].title} — insho topshirig'i"
    if not await _get_assignment(db, courses[0].id, essay_title):
        db.add(
            Assignment(
                course_id=courses[0].id,
                title=essay_title,
                description="Python tilida o'zgaruvchilar va ma'lumot turlari haqida qisqa insho (200-300 so'z).",
                instructions="Mavzu: \"Nega Python o'rganish oson?\" — kamida 3 ta dalil keltiring.",
                type="essay",
                available_from=now() - timedelta(days=3),
                due_date=now() + timedelta(days=10),
                max_score=Decimal("100"),
                pass_score=Decimal("60"),
                weight_percent=Decimal("15"),
                max_attempts=2,
                late_submission_allowed=True,
                late_penalty_per_day=Decimal("5"),
                is_published=True,
                created_by=teacher.id,
            )
        )
        await db.flush()

    # --- (c) Rubrika + rubrika bo'yicha baholangan ish + apellyatsiya ---
    rubric = (
        await db.execute(
            select(Rubric).where(Rubric.title == "SQL topshirig'i — baholash mezonlari")
        )
    ).scalar_one_or_none()
    if rubric is None:
        rubric = Rubric(
            title="SQL topshirig'i — baholash mezonlari",
            description="So'rovlarni baholash uchun standart mezonlar.",
            total_points=Decimal("100"),
            criteria=[
                {"key": "correctness", "name": "To'g'rilik", "max_points": 40,
                 "levels": [{"label": "A'lo", "points": 40}, {"label": "Yaxshi", "points": 28}, {"label": "Past", "points": 12}]},
                {"key": "optimization", "name": "Optimizatsiya", "max_points": 30,
                 "levels": [{"label": "A'lo", "points": 30}, {"label": "Yaxshi", "points": 20}, {"label": "Past", "points": 8}]},
                {"key": "style", "name": "Kod uslubi", "max_points": 30,
                 "levels": [{"label": "A'lo", "points": 30}, {"label": "Yaxshi", "points": 20}, {"label": "Past", "points": 8}]},
            ],
            organization_id=courses[1].organization_id,
            created_by=teacher.id,
        )
        db.add(rubric)
        await db.flush()

    rubric_title = f"{courses[1].title} — SQL so'rovlari (rubrika)"
    rub_assignment = await _get_assignment(db, courses[1].id, rubric_title)
    if rub_assignment is None:
        rub_assignment = Assignment(
            course_id=courses[1].id,
            title=rubric_title,
            description="Berilgan sxema bo'yicha SQL so'rovlarini yozing va .sql fayl sifatida yuklang.",
            instructions="3 ta so'rov: (1) JOIN, (2) agregat, (3) sub-query.",
            type="file",
            available_from=now() - timedelta(days=8),
            due_date=now() - timedelta(days=2),
            max_score=Decimal("100"),
            pass_score=Decimal("60"),
            weight_percent=Decimal("25"),
            allowed_file_types=["sql", "txt", "zip"],
            is_published=True,
            rubric_id=rubric.id,
            created_by=teacher.id,
        )
        db.add(rub_assignment)
        await db.flush()

        graded_sub = Submission(
            assignment_id=rub_assignment.id,
            user_id=main_student.id,
            attempt_number=1,
            files=[{"name": "sql_yechim.sql", "url": "https://cdn.xiuedu.uz/demo/sql_yechim.sql", "mime": "text/plain", "size": 2048}],
            status="graded",
            score=Decimal("82"),
            final_score=Decimal("82"),
            grade_letter="B",
            feedback="JOIN'lar to'g'ri, lekin indeks haqida o'ylash kerak edi.",
            rubric_scores={"correctness": 34, "optimization": 22, "style": 26},
            graded_by=teacher.id,
            graded_at=now() - timedelta(days=1),
        )
        db.add(graded_sub)
        await db.flush()

        # Apellyatsiya (pending) — talaba optimizatsiya ballini qayta ko'rishni so'raydi
        db.add(
            GradeAppeal(
                submission_id=graded_sub.id,
                student_id=main_student.id,
                reason="Optimizatsiya ballini qayta ko'rib chiqishingizni so'rayman — so'rovga indeks qo'shgan edim.",
                status="pending",
            )
        )
        await db.flush()


# ---------------------------------------------------------------------------
# 5c. Imtihonlar (savol turlari + yakunlangan urinish)
# ---------------------------------------------------------------------------


async def _get_exam(db: AsyncSession, course_id: int, title: str):
    return (
        await db.execute(
            select(Exam).where(Exam.course_id == course_id, Exam.title == title)
        )
    ).scalar_one_or_none()


async def _add_question(
    db: AsyncSession,
    exam: Exam,
    *,
    order: int,
    qtype: str,
    title: str,
    points,
    options: list[tuple[str, bool]] | None = None,
    correct_text: str | None = None,
    code_language: str | None = None,
    code_initial: str | None = None,
) -> tuple[Question, list[QuestionOption]]:
    q = Question(
        exam_id=exam.id,
        order_index=order,
        type=qtype,
        title=title,
        points=Decimal(str(points)),
        correct_text=correct_text,
        code_language=code_language,
        code_initial=code_initial,
    )
    db.add(q)
    await db.flush()
    opts: list[QuestionOption] = []
    for i, (text, correct) in enumerate(options or []):
        o = QuestionOption(question_id=q.id, order_index=i, text=text, is_correct=correct)
        db.add(o)
        opts.append(o)
    if opts:
        await db.flush()
    return q, opts


async def seed_exams(
    db: AsyncSession, courses: list[Course], teacher: User, main_student: User
):
    # --- (1) Hozir topshiriladigan QUIZ (proctoringsiz — silliq demo) ---
    quiz_title = f"{courses[0].title} — bilimni tekshirish (quiz)"
    if await _get_exam(db, courses[0].id, quiz_title) is None:
        quiz = Exam(
            course_id=courses[0].id,
            organization_id=courses[0].organization_id,
            title=quiz_title,
            description="Python asoslari bo'yicha qisqa test. Barcha savol turlari namunasi.",
            type="quiz",
            status="published",
            duration_minutes=30,
            max_attempts=2,
            passing_score=Decimal("60"),
            shuffle_questions=False,
            shuffle_options=False,
            show_correct_answers=True,
            proctoring_enabled=False,
            require_face_id=False,
            require_screen_share=False,
            allow_tab_switch=True,
            available_from=now() - timedelta(days=1),
            available_until=now() + timedelta(days=14),
            created_by=teacher.id,
        )
        db.add(quiz)
        await db.flush()
        await _add_question(
            db, quiz, order=0, qtype="single_choice", points=2,
            title="Python dasturlash tili qaysi yilda yaratilgan?",
            options=[("1991", True), ("2000", False), ("1985", False), ("2010", False)],
        )
        await _add_question(
            db, quiz, order=1, qtype="multiple_choice", points=2,
            title="Quyidagilardan qaysilari Python ma'lumot turlari?",
            options=[("list", True), ("dict", True), ("tuple", True), ("matrix", False)],
        )
        await _add_question(
            db, quiz, order=2, qtype="true_false", points=1,
            title="Python — interpretatsiya qilinadigan (interpreted) til.",
            options=[("To'g'ri", True), ("Noto'g'ri", False)],
        )
        await _add_question(
            db, quiz, order=3, qtype="short_text", points=1,
            title="Ro'yxat (list) uzunligini qaytaradigan o'rnatilgan funksiya nomi?",
            correct_text="len",
        )
        await _add_question(
            db, quiz, order=4, qtype="essay", points=2,
            title="Python tilining 3 ta afzalligini qisqacha yozing.",
        )
        await _add_question(
            db, quiz, order=5, qtype="code", points=2,
            title="Ikki sonni qo'shib qaytaradigan add(a, b) funksiyasini yozing.",
            code_language="python",
            code_initial="def add(a, b):\n    # kodingizni yozing\n    pass",
        )
        await _add_question(
            db, quiz, order=6, qtype="file_upload", points=2,
            title="Yozgan kodingizni .py yoki .txt fayl sifatida yuklang.",
        )
        await db.flush()

    # --- (2) Kelgusi ORALIQ NAZORAT (proctoring bilan, hali ochilmagan) ---
    mid_title = f"{courses[1].title} — oraliq nazorat"
    if await _get_exam(db, courses[1].id, mid_title) is None:
        midterm = Exam(
            course_id=courses[1].id,
            organization_id=courses[1].organization_id,
            title=mid_title,
            description="SQL bo'yicha oraliq nazorat. Proktoring (kamera + yuz tekshiruvi) majburiy.",
            type="midterm",
            status="published",
            duration_minutes=60,
            max_attempts=1,
            passing_score=Decimal("60"),
            proctoring_enabled=True,
            require_face_id=True,
            require_screen_share=True,
            allow_tab_switch=False,
            available_from=now() + timedelta(days=3),
            available_until=now() + timedelta(days=3, hours=4),
            created_by=teacher.id,
        )
        db.add(midterm)
        await db.flush()
        await _add_question(
            db, midterm, order=0, qtype="single_choice", points=3,
            title="SQL'da qatorlarni shart bo'yicha filtrlash uchun qaysi kalit so'z ishlatiladi?",
            options=[("WHERE", True), ("SELECT", False), ("ORDER BY", False), ("GROUP BY", False)],
        )
        await _add_question(
            db, midterm, order=1, qtype="multiple_choice", points=3,
            title="Quyidagilardan qaysilari JOIN turlari?",
            options=[("INNER JOIN", True), ("LEFT JOIN", True), ("RIGHT JOIN", True), ("ROUND JOIN", False)],
        )
        await _add_question(
            db, midterm, order=2, qtype="short_text", points=2,
            title="Jadvaldagi barcha ustunlarni tanlash uchun ishlatiladigan belgi?",
            correct_text="*",
        )
        await db.flush()

    # --- (3) Yakunlangan QUIZ + baholangan urinish (natija + review demo) ---
    done_title = f"{courses[2].title} — yakuniy test"
    if await _get_exam(db, courses[2].id, done_title) is None:
        done = Exam(
            course_id=courses[2].id,
            organization_id=courses[2].organization_id,
            title=done_title,
            description="Web asoslari bo'yicha yakuniy test (topshirilgan).",
            type="quiz",
            status="published",
            duration_minutes=30,
            max_attempts=1,
            passing_score=Decimal("60"),
            show_correct_answers=True,
            proctoring_enabled=False,
            require_face_id=False,
            require_screen_share=False,
            available_from=now() - timedelta(days=5),
            available_until=now() - timedelta(days=1),
            created_by=teacher.id,
        )
        db.add(done)
        await db.flush()
        q1, o1 = await _add_question(
            db, done, order=0, qtype="single_choice", points=2,
            title="HTML nimaning qisqartmasi?",
            options=[("HyperText Markup Language", True), ("High Text Machine Language", False),
                     ("Hyperlink Markup Logic", False), ("Home Tool Markup Language", False)],
        )
        q2, o2 = await _add_question(
            db, done, order=1, qtype="multiple_choice", points=3,
            title="Quyidagilardan qaysilari CSS xossalari (property)?",
            options=[("color", True), ("margin", True), ("padding", True), ("function", False)],
        )
        q3, o3 = await _add_question(
            db, done, order=2, qtype="true_false", points=2,
            title="CSS — to'liq dasturlash tili.",
            options=[("To'g'ri", False), ("Noto'g'ri", True)],
        )
        q4, _o4 = await _add_question(
            db, done, order=3, qtype="short_text", points=3,
            title="Sahifa sarlavhasini belgilovchi HTML teg nomi?",
            correct_text="title",
        )
        await db.flush()

        started = now() - timedelta(days=2)
        attempt = ExamAttempt(
            exam_id=done.id,
            user_id=main_student.id,
            attempt_number=1,
            status="graded",
            started_at=started,
            submitted_at=started + timedelta(minutes=22),
            deadline_at=started + timedelta(minutes=30),
            time_spent_seconds=22 * 60,
            auto_score=Decimal("7"),
            total_score=Decimal("7"),
            max_score=Decimal("10"),
            percentage=Decimal("70"),
            passed=True,
            question_order=[q1.id, q2.id, q3.id, q4.id],
        )
        db.add(attempt)
        await db.flush()

        # Javoblar: Q1 to'g'ri(2), Q2 to'g'ri(3), Q3 to'g'ri(2), Q4 noto'g'ri(0) = 7/10
        db.add_all([
            Answer(
                attempt_id=attempt.id, question_id=q1.id,
                selected_option_ids=[o1[0].id],
                auto_correct=True, points_earned=Decimal("2"), points_max=Decimal("2"),
            ),
            Answer(
                attempt_id=attempt.id, question_id=q2.id,
                selected_option_ids=[o2[0].id, o2[1].id, o2[2].id],
                auto_correct=True, points_earned=Decimal("3"), points_max=Decimal("3"),
            ),
            Answer(
                attempt_id=attempt.id, question_id=q3.id,
                selected_option_ids=[o3[1].id],
                auto_correct=True, points_earned=Decimal("2"), points_max=Decimal("2"),
            ),
            Answer(
                attempt_id=attempt.id, question_id=q4.id,
                text_answer="header",
                auto_correct=False, points_earned=Decimal("0"), points_max=Decimal("3"),
            ),
        ])
        await db.flush()


# ---------------------------------------------------------------------------
# 6. Live darslar
# ---------------------------------------------------------------------------


async def seed_live(
    db: AsyncSession, courses: list[Course], teacher: User, students: list[User]
):
    course = courses[0]
    # Kelgusi live dars
    upcoming_title = f"{course.title} — jonli amaliyot #1"
    exists = (
        await db.execute(
            select(LiveSession).where(LiveSession.title == upcoming_title)
        )
    ).scalar_one_or_none()
    if exists is None:
        start = now() + timedelta(days=2, hours=1)
        db.add(
            LiveSession(
                organization_id=course.organization_id,
                course_id=course.id,
                title=upcoming_title,
                description="Python funksiyalari bo'yicha jonli amaliy mashg'ulot.",
                scheduled_start=start,
                scheduled_end=start + timedelta(minutes=90),
                duration_minutes=90,
                provider="native",
                host_user_id=teacher.id,
                status="scheduled",
            )
        )
        await db.flush()

    # O'tib ketgan live dars + davomat
    past_title = f"{course.title} — kirish darsi"
    past = (
        await db.execute(select(LiveSession).where(LiveSession.title == past_title))
    ).scalar_one_or_none()
    if past is None:
        pstart = now() - timedelta(days=5)
        past = LiveSession(
            organization_id=course.organization_id,
            course_id=course.id,
            title=past_title,
            description="Kursga kirish va umumiy tanishuv.",
            scheduled_start=pstart,
            scheduled_end=pstart + timedelta(minutes=60),
            duration_minutes=60,
            provider="native",
            host_user_id=teacher.id,
            status="ended",
            actual_start=pstart,
            actual_end=pstart + timedelta(minutes=58),
        )
        db.add(past)
        await db.flush()
        for s in students:
            db.add(
                LiveAttendance(
                    session_id=past.id,
                    user_id=s.id,
                    joined_at=pstart + timedelta(minutes=1),
                    left_at=pstart + timedelta(minutes=57),
                    total_minutes=56,
                    is_counted=True,
                )
            )
        await db.flush()

        # Demo yozuv (MinIO'ga oldindan yuklangan video) — playback oqimini ko'rsatish uchun.
        # GET'da recording_url avtomatik presigned URL bilan almashtiriladi (Phase 7b).
        rec_key = "live-recordings/demo/intro.mp4"
        rec_url = "http://localhost:8212/lms-files/live-recordings/demo/intro.mp4"
        rec_size = 114452
        rec_dur = 8
        past.recording_url = rec_url
        past.recording_size_bytes = rec_size
        past.recording_duration_seconds = rec_dur
        past.recording_mime_type = "video/mp4"
        db.add(
            LiveRecording(
                session_id=past.id,
                recorded_by=teacher.id,
                status="finalized",
                object_key=rec_key,
                url=rec_url,
                mime_type="video/mp4",
                started_at=pstart + timedelta(minutes=2),
                finalized_at=pstart + timedelta(minutes=58),
                duration_seconds=rec_dur,
                file_size_bytes=rec_size,
            )
        )
        await db.flush()


# ---------------------------------------------------------------------------
# 7. Forum
# ---------------------------------------------------------------------------


async def seed_forum(
    db: AsyncSession, course: Course, teacher: User, students: list[User]
):
    ann_title = "E'lon: kurs jadvali va baholash mezonlari"
    ann = (
        await db.execute(
            select(ForumThread).where(
                ForumThread.course_id == course.id, ForumThread.title == ann_title
            )
        )
    ).scalar_one_or_none()
    if ann is None:
        db.add(
            ForumThread(
                course_id=course.id,
                author_id=teacher.id,
                title=ann_title,
                body="Hurmatli talabalar, kurs har hafta yangilanadi. Topshiriqlar muddatiga e'tibor bering.",
                is_pinned=True,
                is_announcement=True,
                view_count=42,
            )
        )
        await db.flush()

    q_title = "Funksiyalarda return va print farqi nimada?"
    thread = (
        await db.execute(
            select(ForumThread).where(
                ForumThread.course_id == course.id, ForumThread.title == q_title
            )
        )
    ).scalar_one_or_none()
    if thread is None:
        thread = ForumThread(
            course_id=course.id,
            author_id=students[0].id,
            title=q_title,
            body="Darsdagi misolda return ishlatildi, lekin print ham natija chiqaryapti. Farqini tushuntirib bera olasizmi?",
            view_count=27,
        )
        db.add(thread)
        await db.flush()

        posts = [
            (teacher.id, "print ekranga chiqaradi, return esa qiymatni funksiyadan qaytaradi — uni keyin boshqa joyda ishlatish mumkin."),
            (students[1].id, "Rahmat, endi tushundim! return bo'lmasa funksiya None qaytarar ekan."),
        ]
        last = None
        for author_id, body in posts:
            p = ForumPost(thread_id=thread.id, author_id=author_id, body=body)
            db.add(p)
            last = p
        await db.flush()
        thread.post_count = len(posts)
        thread.last_reply_at = last.created_at if last else None
        await db.flush()


# ---------------------------------------------------------------------------
# 8. Sertifikat (tugatilgan kurs uchun)
# ---------------------------------------------------------------------------


async def seed_certificate(db: AsyncSession, course: Course, student: User, org):
    exists = (
        await db.execute(
            select(Certificate).where(
                Certificate.user_id == student.id, Certificate.course_id == course.id
            )
        )
    ).scalar_one_or_none()
    if exists:
        return
    cert = Certificate(
        user_id=student.id,
        course_id=course.id,
        certificate_number="XIU-2026-000123",
        verification_code="A1B2C3D4E5F6G7H8",
        score_percentage=Decimal("92.50"),
        issued_at=now() - timedelta(days=1),
    )
    db.add(cert)
    await db.flush()

    # Kreativ PDF generatsiya + MinIO (download tugmasi ishlashi uchun)
    from app.core.storage import upload_object
    from app.modules.certificates.pdf import render_certificate_pdf
    from app.modules.certificates.service import _verification_url

    pdf_bytes = render_certificate_pdf(
        student_name=student.full_name,
        course_title=course.title,
        certificate_number=cert.certificate_number,
        issued_at=cert.issued_at,
        verification_url=_verification_url(cert.verification_code),
        organization_name=org.name,
        score_percentage=float(cert.score_percentage),
    )
    obj = f"certificates/{cert.id}/{cert.certificate_number}.pdf"
    try:
        upload_object(object_name=obj, data=pdf_bytes, content_type="application/pdf")
        cert.pdf_path = obj
    except Exception:  # noqa: BLE001
        pass
    await db.flush()


# ---------------------------------------------------------------------------
# 9. Gamifikatsiya
# ---------------------------------------------------------------------------


async def seed_gamification(
    db: AsyncSession, students: list[User], courses: list[Course]
):
    """Gamification'ni HAQIQIY harakatlar orqali seed qiladi (sabab bilan).

    Sehrli ball/nishon yo'q — hammasi `award_event` orqali real kurs/dars/imtihon
    context'i bilan beriladi. Shu tufayli har nishonning aniq sababi bor, ballar
    event'lar yig'indisiga teng, progress (masalan course_master 1/5) ko'rinadi.
    """
    from app.modules.gamification import service as gamif

    course = courses[0]
    lessons = await course_lessons(db, course)
    exam = (
        await db.execute(
            select(Exam).where(Exam.course_id == course.id).order_by(Exam.id)
        )
    ).scalars().first()

    # (tugatilgan dars soni, kurs tugadi?, imtihon 100%?, izoh soni)
    # main — first_lesson + first_course + exam_ace; qolganlar kamayib boradi
    journeys = [
        (min(6, len(lessons)), True, True, 3),
        (min(5, len(lessons)), True, False, 1),
        (min(4, len(lessons)), False, False, 0),
        (min(3, len(lessons)), False, False, 0),
        (min(2, len(lessons)), False, False, 0),
    ]

    for idx, student in enumerate(students):
        n_lessons, complete_course, perfect_exam, n_comments = (
            journeys[idx] if idx < len(journeys) else (1, False, False, 0)
        )

        for li in range(n_lessons):
            lesson = lessons[li]
            await gamif.award_event(
                db,
                user_id=student.id,
                event_type="lesson.completed",
                context={"lesson_id": lesson.id, "course_id": course.id},
                dedupe_key=f"lesson.completed:{student.id}:{lesson.id}",
            )

        if complete_course:
            await gamif.award_event(
                db,
                user_id=student.id,
                event_type="course.completed",
                context={"course_id": course.id},
                dedupe_key=f"course.completed:{student.id}:{course.id}",
            )

        if perfect_exam and exam is not None:
            await gamif.award_event(
                db,
                user_id=student.id,
                event_type="exam.passed",
                context={"exam_id": exam.id},
                dedupe_key=f"demo.exam.passed:{student.id}:{exam.id}",
            )
            await gamif.award_event(
                db,
                user_id=student.id,
                event_type="exam.perfect",
                context={"exam_id": exam.id},
                dedupe_key=f"demo.exam.perfect:{student.id}:{exam.id}",
            )

        for ci in range(n_comments):
            await gamif.award_event(
                db,
                user_id=student.id,
                event_type="comment.created",
                context={"seq": ci},
                dedupe_key=f"demo.comment:{student.id}:{ci}",
            )

    await db.flush()


# ---------------------------------------------------------------------------
# 10. Bildirishnomalar (asosiy talaba uchun)
# ---------------------------------------------------------------------------


async def seed_notifications(db: AsyncSession, student: User, course: Course):
    notes = [
        ("live.scheduled", "Yangi jonli dars rejalashtirildi", f"{course.title} — jonli amaliyot 2 kundan keyin boshlanadi.", "/app/live"),
        ("exam.graded", "Topshirig'ingiz baholandi", "Amaliy topshiriq uchun 88 ball oldingiz.", "/app/assignments"),
        ("system", "XIU LMS ga xush kelibsiz!", "Profilingizni to'ldiring va birinchi kursingizni boshlang.", "/app/profile"),
    ]
    for event_type, title, body, url in notes:
        exists = (
            await db.execute(
                select(Notification).where(
                    Notification.user_id == student.id, Notification.title == title
                )
            )
        ).scalar_one_or_none()
        if exists:
            continue
        db.add(
            Notification(
                user_id=student.id,
                event_type=event_type,
                title=title,
                body=body,
                action_url=url,
            )
        )
    await db.flush()


# ---------------------------------------------------------------------------
# 11. Baholar semestr tarixi (Phase 25)
# ---------------------------------------------------------------------------


async def seed_grade_history(
    db: AsyncSession, courses: list[Course], teacher: User, main_student: User, org
):
    # (a) Joriy enrollmentlarni Bahorgi semestrga taglash
    for course in courses[:4]:
        enr = (
            await db.execute(
                select(Enrollment).where(
                    Enrollment.course_id == course.id,
                    Enrollment.user_id == main_student.id,
                )
            )
        ).scalar_one_or_none()
        if enr and not enr.semester:
            enr.academic_year = "2025-2026"
            enr.semester = "Bahorgi semestr"
    await db.flush()

    # (b) O'tgan semestr (Kuzgi) — 3 yakunlangan kurs + yakuniy baho
    past = [
        ("oliy-matematika", "Oliy matematika", Decimal("91")),
        ("fizika-asoslari", "Fizika asoslari", Decimal("76")),
        ("ingliz-tili-b1", "Ingliz tili (B1)", Decimal("84")),
    ]
    pstart = now() - timedelta(days=180)
    for slug, title, grade in past:
        course = (
            await db.execute(select(Course).where(Course.slug == slug))
        ).scalar_one_or_none()
        if course is None:
            course = Course(
                title=title,
                slug=slug,
                organization_id=org.id,
                type="academic",
                language="uz-lat",
                status="published",
                published_at=pstart,
                enrollment_type="manual",
                primary_author_id=teacher.id,
            )
            db.add(course)
            await db.flush()
        exists = (
            await db.execute(
                select(Enrollment).where(
                    Enrollment.course_id == course.id,
                    Enrollment.user_id == main_student.id,
                )
            )
        ).scalar_one_or_none()
        if exists is None:
            db.add(
                Enrollment(
                    course_id=course.id,
                    user_id=main_student.id,
                    enrollment_method="auto",
                    completion_status="completed",
                    completed_at=pstart + timedelta(days=120),
                    final_grade=grade,
                    academic_year="2025-2026",
                    semester="Kuzgi semestr",
                    enrolled_at=pstart,
                )
            )
    await db.flush()


# ---------------------------------------------------------------------------
# 12. Chat (suhbatlar) — Phase 26
# ---------------------------------------------------------------------------


async def _seed_direct_chat(
    db: AsyncSession, a_id: int, b_id: int, msgs: list[tuple[int, str]], *, a_read: bool
):
    """a_id va b_id orasida direct suhbat + xabarlar. a_read=False bo'lsa a uchun
    o'qilmagan xabar qoladi (sidebar badge uchun).
    """
    conv = Conversation(type="direct")
    db.add(conv)
    await db.flush()
    base = now() - timedelta(hours=3)
    last_at = base
    for i, (sid, body) in enumerate(msgs):
        at = base + timedelta(minutes=i * 5)
        db.add(Message(conversation_id=conv.id, sender_id=sid, body=body, created_at=at))
        last_at = at
    await db.flush()
    conv.last_message_at = last_at
    db.add_all(
        [
            ConversationMember(
                conversation_id=conv.id,
                user_id=a_id,
                role="member",
                last_read_at=last_at if a_read else None,
            ),
            ConversationMember(
                conversation_id=conv.id, user_id=b_id, role="member", last_read_at=last_at
            ),
        ]
    )
    await db.flush()


async def seed_chat(
    db: AsyncSession, main_student: User, teacher: User, extra_students: list[User]
):
    # Idempotent — talabada suhbat bo'lsa o'tkazib yuboramiz
    existing = (
        await db.execute(
            select(ConversationMember).where(
                ConversationMember.user_id == main_student.id
            )
        )
    ).first()
    if existing:
        return

    # 1) Talaba ↔ O'qituvchi (1 o'qilmagan qoldiramiz)
    await _seed_direct_chat(
        db,
        main_student.id,
        teacher.id,
        [
            (main_student.id, "Assalomu alaykum, ustoz! Topshiriq bo'yicha savol bor edi."),
            (teacher.id, "Va alaykum assalom! Marhamat, qanday savol?"),
            (main_student.id, "Rubrikada optimizatsiya qismini to'liq tushunmadim."),
            (teacher.id, "Indekslar haqida darsdagi 3-bo'limni ko'ring — u yerda misol bor."),
        ],
        a_read=False,
    )

    # 2) Talaba ↔ Kursdosh (o'qilgan)
    if extra_students:
        mate = extra_students[0]
        await _seed_direct_chat(
            db,
            main_student.id,
            mate.id,
            [
                (mate.id, "Salom! Bugungi jonli darsga ulanasanmi?"),
                (main_student.id, "Ha, albatta. Ertaga SQL imtihoni ham bor-ku."),
                (mate.id, "Ha, birga tayyorlanaylik."),
            ],
            a_read=True,
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    async with SessionLocal() as db:
        org = await ensure_xiu_org(db)

        # Kerakli rollar/userlar (seed.py oldin ishga tushirilgan bo'lishi kerak)
        roles = {
            r.code: r for r in (await db.execute(select(Role))).scalars().all()
        }
        student_role = roles.get("student")
        teacher = await get_user(db, "teacher@xiuedu.uz")
        dean = await get_user(db, "dean@xiuedu.uz")
        dep_head = await get_user(db, "dep-head@xiuedu.uz")
        main_student = await get_user(db, "student@xiuedu.uz")

        if not all([student_role, teacher, dean, dep_head, main_student]):
            raise SystemExit(
                "Avval `python -m app.db.seed` ishga tushiring (rollar + demo userlar kerak)."
            )

        # 1. Talabalar
        extra_students = await seed_students(db, student_role)
        all_students = [main_student] + extra_students

        # 2. Akademik tuzilma
        faculty, department, specialty, subjects, group, semester = await seed_academic(
            db, org, dean, dep_head
        )
        await assign_student_fields(db, all_students, group, org)
        teacher.tenant_id = org.id
        teacher.staff_position = "teacher"
        await db.flush()

        # 3. Kurslar
        courses = await seed_courses(db, org, teacher, subjects)

        # 4. Enrollment + progress
        # Birinchi 4 kurs — asosiy talaba yozilgan; oxirgi 2 kurs katalogda
        # "kashf qilinadigan" (hech kim yozilmagan) bo'lib qoladi.
        progress_plan = [1.0, 0.6, 0.25, 0.0]  # main student shu kurslar bo'yicha
        for c_idx, course in enumerate(courses):
            if c_idx >= len(progress_plan):
                continue  # kashf qilinadigan kurslar — enrollmentsiz
            lessons = await course_lessons(db, course)
            # Asosiy talaba
            status = "completed" if progress_plan[c_idx] >= 1.0 else "in_progress"
            enr = await enroll(db, course, main_student, status=status)
            if status == "completed" and enr.completed_at is None:
                enr.completed_at = now() - timedelta(days=1)
                enr.final_grade = Decimal("92.50")
            await set_progress(db, main_student, lessons, progress_plan[c_idx])
            # Qo'shimcha talabalar — birinchi 2 kursga
            if c_idx < 2:
                for s in extra_students:
                    await enroll(db, course, s)
                    await set_progress(db, s, lessons, 0.5)
        await db.flush()

        # 5. Reviews (1-kurs)
        review_data = [
            (extra_students[0], 5, "Juda tushunarli kurs, ustozga rahmat!"),
            (extra_students[1], 4, "Yaxshi, lekin amaliy mashqlar ko'proq bo'lsa edi."),
            (extra_students[2], 5, "Noldan o'rganmoqchilar uchun ideal."),
        ]
        for user, rating, comment in review_data:
            exists = (
                await db.execute(
                    select(CourseReview).where(
                        CourseReview.course_id == courses[0].id,
                        CourseReview.user_id == user.id,
                    )
                )
            ).scalar_one_or_none()
            if exists is None:
                db.add(
                    CourseReview(
                        course_id=courses[0].id,
                        user_id=user.id,
                        rating=rating,
                        comment=comment,
                    )
                )
        await db.flush()

        # 6-10
        await seed_assignments(db, courses, teacher, main_student)
        await seed_exams(db, courses, teacher, main_student)
        await seed_live(db, courses, teacher, all_students)
        await seed_grade_history(db, courses, teacher, main_student, org)
        await seed_chat(db, main_student, teacher, extra_students)
        await seed_forum(db, courses[0], teacher, all_students)
        await seed_certificate(db, courses[0], main_student, org)
        await seed_gamification(db, all_students, courses)
        await seed_notifications(db, main_student, courses[0])

        await db.commit()

    print("✓ Demo ma'lumotlar muvaffaqiyatli yuklandi")
    print(f"  Fakultet: {faculty.name}")
    print(f"  Kafedra: {department.name}")
    print(f"  Yo'nalish: {specialty.name} ({specialty.code})")
    print(f"  Guruh: {group.name}")
    print(f"  Fanlar: {len(subjects)} ta")
    print(f"  Kurslar: {len(courses)} ta (modul + dars + kontent bilan)")
    print(f"  Talabalar: {len(all_students)} ta (asosiy: student@xiuedu.uz)")
    print()
    print("  Asosiy talaba (student@xiuedu.uz) holati:")
    print("   - 4 kursga yozilgan (1 tugatilgan, sertifikat bilan)")
    print("   - Topshiriq baholandi (88 ball), 3 o'qilmagan bildirishnoma")
    print("   - Kelgusi jonli dars, forum, gamifikatsiya balli")


if __name__ == "__main__":
    asyncio.run(main())

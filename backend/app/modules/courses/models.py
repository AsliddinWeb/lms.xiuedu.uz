"""Courses moduli — Phase 3b (Course / Module / Lesson / Enrollment / LessonProgress).

Spec: docs/03-modules/06-courses.md (MVP versiyasi).

Tuzilma:
    Course
      └── Module (order_index)
            └── Lesson (order_index, primary_content_id → ContentItem)

Yozilish:
    Enrollment (course_id, user_id) — UNIQUE
    LessonProgress (user_id, lesson_id) — UNIQUE

Phase 3b scope'idan tashqari (kelajakda qo'shiladi):
- CourseAuthor many-to-many (hozirgi MVP'da `primary_author_id` yetadi)
- Module/Lesson lock logikasi (Phase 4+ — `unlock_after_*_id`)
- Certificate generation Celery worker (Phase 5+)
- Forum / Q&A (Phase 11)
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IDMixin, SoftDeleteMixin, TimestampMixin


class Course(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Kurs — Module + Lesson tuzilmasini birlashtiradi."""

    __tablename__ = "courses"

    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Akademik bog'lanish (akademik kurs uchun) yoki bo'sh (open kurs uchun).
    subject_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("subjects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    organization_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # 'academic' | 'open' | 'micro' | 'specialization'
    type: Mapped[str] = mapped_column(String(20), default="academic", nullable=False)
    # 'beginner' | 'intermediate' | 'advanced'
    level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="uz-lat", nullable=False)

    cover_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    trailer_video_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    duration_weeks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)

    objectives: Mapped[list[str]] = mapped_column(
        ARRAY(String(500)), default=list, nullable=False
    )
    skills_gained: Mapped[list[str]] = mapped_column(
        ARRAY(String(500)), default=list, nullable=False
    )

    # 'draft' | 'published' | 'archived'
    status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False, index=True
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 'auto' | 'manual' | 'self'
    enrollment_type: Mapped[str] = mapped_column(
        String(20), default="manual", nullable=False
    )
    max_students: Mapped[int | None] = mapped_column(Integer, nullable=True)

    primary_author_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    modules: Mapped[list["Module"]] = relationship(
        "Module",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Module.order_index",
    )
    enrollments: Mapped[list["Enrollment"]] = relationship(
        "Enrollment", back_populates="course", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Phase 8c — public/admin kurs ro'yxati uchun (status + organization filtr)
        Index("ix_courses_status_org", "status", "organization_id"),
    )

    def __repr__(self) -> str:
        return f"<Course id={self.id} slug={self.slug} status={self.status}>"


class Module(Base, IDMixin, TimestampMixin):
    """Kurs ichidagi modul (bo'lim)."""

    __tablename__ = "modules"

    course_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("courses.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    available_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    available_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    course: Mapped[Course] = relationship("Course", back_populates="modules")
    lessons: Mapped[list["Lesson"]] = relationship(
        "Lesson",
        back_populates="module",
        cascade="all, delete-orphan",
        order_by="Lesson.order_index",
    )

    def __repr__(self) -> str:
        return f"<Module id={self.id} course_id={self.course_id} idx={self.order_index}>"


class Lesson(Base, IDMixin, TimestampMixin):
    """Modul ichidagi dars — ContentItem'ga yo'naltirilgan."""

    __tablename__ = "lessons"

    module_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("modules.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    primary_content_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("content_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_required_for_completion: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    module: Mapped[Module] = relationship("Module", back_populates="lessons")

    def __repr__(self) -> str:
        return f"<Lesson id={self.id} module_id={self.module_id} idx={self.order_index}>"


class Enrollment(Base, IDMixin):
    """Talabaning kursga yozilishi (UNIQUE course_id+user_id)."""

    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("course_id", "user_id", name="uq_enrollment_course_user"),
    )

    course_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("courses.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # 'auto' | 'manual' | 'self'
    enrollment_method: Mapped[str] = mapped_column(
        String(20), default="self", nullable=False
    )
    enrolled_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # 'in_progress' | 'completed' | 'failed' | 'dropped'
    completion_status: Mapped[str] = mapped_column(
        String(20), default="in_progress", nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    final_grade: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    course: Mapped[Course] = relationship("Course", back_populates="enrollments")

    def __repr__(self) -> str:
        return f"<Enrollment course={self.course_id} user={self.user_id} {self.completion_status}>"


class LessonProgress(Base, IDMixin):
    """Talabaning dars bo'yicha progressi (UNIQUE user_id+lesson_id)."""

    __tablename__ = "lesson_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="uq_progress_user_lesson"),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    lesson_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("lessons.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    progress_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0"), nullable=False
    )
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_position: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<LessonProgress user={self.user_id} lesson={self.lesson_id} "
            f"{self.progress_percent}%>"
        )

"""Akademik tuzilma modellari.

Hierarchy:
    Organization → Faculty → Department → Specialty → Curriculum → Subjects

Spec: docs/03-modules/03-academic.md
559-qaror:
  - 14-band: distance_enabled flag (faqat ruxsat berilgan yo'nalishlar)
  - 15-band: bakalavr annual_quota ≤ 300, magistr ≤ 30
  - 8-band: multi-tenant — har OTM o'z scope'ida
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IDMixin, TimestampMixin


class Faculty(Base, IDMixin, TimestampMixin):
    """Fakultet — Organization ostida.

    Phase 10b — HEMIS bog'lanish: `hemis_id`, `hemis_code` HEMIS Department schema'dan
    keladi. Backend API `/v1/data/department-list` orqali sync qilinadi.
    """

    __tablename__ = "faculties"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_faculty_org_code"),)

    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dean_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Phase 10b — HEMIS integration
    hemis_id: Mapped[int | None] = mapped_column(
        Integer, unique=True, index=True, nullable=True
    )
    hemis_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hemis_parent_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 'university' | 'faculty' | 'department' — HEMIS structureType
    structure_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # 'city' | 'rural' — HEMIS localityType
    locality_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    departments: Mapped[list["Department"]] = relationship(
        "Department", back_populates="faculty", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Faculty {self.code} ({self.name})>"


class Department(Base, IDMixin, TimestampMixin):
    """Kafedra — Faculty ostida."""

    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("faculty_id", "code", name="uq_department_faculty_code"),
    )

    faculty_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("faculties.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    head_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    faculty: Mapped[Faculty] = relationship("Faculty", back_populates="departments")
    specialties: Mapped[list["Specialty"]] = relationship(
        "Specialty", back_populates="department", cascade="all, delete-orphan"
    )
    subjects: Mapped[list["Subject"]] = relationship(
        "Subject", back_populates="department", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Department {self.code}>"


class Specialty(Base, IDMixin, TimestampMixin):
    """Yo'nalish/Mutaxassislik — Department ostida.

    559-qaror 14-band: `distance_enabled` flag.
    559-qaror 15-band: `annual_quota` — bakalavr 300, magistr 30.
    """

    __tablename__ = "specialties"

    department_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("departments.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    code: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )  # DTS kodi: '60611100'
    # Phase 10b — HEMIS classifier code (Specialty schema'da `code`)
    hemis_code: Mapped[str | None] = mapped_column(
        String(50), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)

    # 'bachelor' | 'master' | 'phd'
    level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    duration_years: Mapped[int] = mapped_column(Integer, nullable=False)

    # 'fulltime' | 'parttime' | 'evening' | 'distance'
    education_form: Mapped[str] = mapped_column(String(20), nullable=False)

    # 'uz-lat' | 'uz-cyr' | 'ru' | 'en'
    language: Mapped[str] = mapped_column(String(10), nullable=False)

    distance_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    annual_quota: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    department: Mapped[Department] = relationship("Department", back_populates="specialties")
    curricula: Mapped[list["Curriculum"]] = relationship(
        "Curriculum", back_populates="specialty", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Specialty {self.code} {self.level}>"


class Subject(Base, IDMixin, TimestampMixin):
    """Fan — Department bazasida."""

    __tablename__ = "subjects"

    department_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("departments.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    lecture_hours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    practice_hours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    seminar_hours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    self_study_hours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    language: Mapped[str] = mapped_column(String(10), default="uz-lat", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    department: Mapped[Department] = relationship("Department", back_populates="subjects")
    prerequisites: Mapped[list["Subject"]] = relationship(
        "Subject",
        secondary="subject_prerequisites",
        primaryjoin="Subject.id == SubjectPrerequisite.subject_id",
        secondaryjoin="Subject.id == SubjectPrerequisite.prerequisite_id",
        viewonly=True,
    )

    def __repr__(self) -> str:
        return f"<Subject {self.code}>"


class SubjectPrerequisite(Base):
    """Pre-rekvizit junction (subject avval prerequisite o'tilishi kerak)."""

    __tablename__ = "subject_prerequisites"

    subject_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("subjects.id", ondelete="CASCADE"), primary_key=True
    )
    prerequisite_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("subjects.id", ondelete="CASCADE"), primary_key=True
    )


class Curriculum(Base, IDMixin, TimestampMixin):
    """O'quv reja — Specialty uchun versiyalanadi.

    Spec: docs/03-modules/03-academic.md (4-bo'lim).
    """

    __tablename__ = "curricula"

    specialty_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("specialties.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str | None] = mapped_column(String(20), nullable=True)  # '2026-v1'
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)

    # 'DTS' | 'professional_standard' (OʻzDSt 36.2030, 559-qaror 9-band)
    based_on: Mapped[str | None] = mapped_column(String(50), nullable=True)
    standard_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    total_credits: Mapped[int] = mapped_column(Integer, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    approved_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Phase 10b — HEMIS sync (Curriculum id)
    hemis_id: Mapped[int | None] = mapped_column(
        Integer, unique=True, nullable=True
    )

    specialty: Mapped[Specialty] = relationship("Specialty", back_populates="curricula")
    curriculum_subjects: Mapped[list["CurriculumSubject"]] = relationship(
        "CurriculumSubject", back_populates="curriculum", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Curriculum {self.specialty_id}/{self.version}>"


class CurriculumSubject(Base, IDMixin):
    """O'quv rejada fan + semestr taqsimoti."""

    __tablename__ = "curriculum_subjects"
    __table_args__ = (
        UniqueConstraint(
            "curriculum_id", "subject_id", "semester", name="uq_curr_subject_semester"
        ),
    )

    curriculum_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("curricula.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    subject_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False
    )
    semester: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, 3...
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    curriculum: Mapped[Curriculum] = relationship(
        "Curriculum", back_populates="curriculum_subjects"
    )
    subject: Mapped[Subject] = relationship("Subject")


class AcademicCalendar(Base, IDMixin, TimestampMixin):
    """Akademik kalendar — har OTM, har o'quv yili.

    semesters va holidays JSONB sifatida saqlanadi (struktura erkin).
    Misol semesters: [{"name":"Kuzgi","start":"2026-09-01","end":"2027-01-15"}]
    """

    __tablename__ = "academic_calendars"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "academic_year", name="uq_calendar_org_year"
        ),
    )

    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)  # '2026-2027'
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    semesters: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    holidays: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<AcademicCalendar {self.academic_year} org={self.organization_id}>"


# ============================================================================
# Phase 10b — HEMIS sync entities
# ============================================================================


class AcademicGroup(Base, IDMixin, TimestampMixin):
    """Akademik guruh — HEMIS `Group` ga to'g'ri keladi.

    Talaba bitta guruhga biriktirilgan (`User.group_id`). HEMIS Backend API'dan
    sync'da quyiladi: `/v1/data/group-list`.
    """

    __tablename__ = "academic_groups"

    # HEMIS primary
    hemis_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # masalan "ATM-21-1"
    education_lang: Mapped[str | None] = mapped_column(String(20), nullable=True)
    faculty_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("faculties.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    specialty_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("specialties.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    semester_hemis_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    hemis_last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    faculty: Mapped[Faculty | None] = relationship("Faculty", lazy="joined")
    specialty: Mapped[Specialty | None] = relationship("Specialty", lazy="joined")

    def __repr__(self) -> str:
        return f"<AcademicGroup {self.name} hemis={self.hemis_id}>"


class AcademicSemester(Base, IDMixin):
    """HEMIS Semester — current semester pointer.

    HEMIS `Semester` schemasi: `{ id, code, name, current, education_year }`.
    Bizning `User.current_semester_id` shu jadvalga ishora qiladi (loose FK, hemis_id orqali).
    """

    __tablename__ = "academic_semesters"

    hemis_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    education_year_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    education_year_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hemis_last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<AcademicSemester {self.name} current={self.is_current}>"


class HemisClassifier(Base):
    """HEMIS klassifikator registri — yagona joyda saqlanadi.

    HEMIS API'da har joyda `{code, name}` pari uchraydi (educationForm, paymentForm,
    studentStatus, country, socialCategory, va h.k.). Bizda alohida enumlar o'rniga
    bitta jadval — `type` field bilan ajratiladi.

    Misol:
        type='education_form', code='full_time', name='Kunduzgi'
        type='payment_form',  code='contract',  name='Kontrakt'
    """

    __tablename__ = "hemis_classifiers"

    type: Mapped[str] = mapped_column(String(50), primary_key=True)
    code: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    hemis_last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<HemisClassifier {self.type}/{self.code}>"

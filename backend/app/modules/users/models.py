"""User va Profile modellari.

Spec: docs/03-modules/01-auth.md, docs/03-modules/02-users-rbac.md
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IDMixin, SoftDeleteMixin, TimestampMixin


class User(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """LMS foydalanuvchisi.

    Phase 10b — HEMIS-first identity:
        - `hemis_id` (HEMIS integer ID) — talaba/o'qituvchi uchun primary external ID
        - `hemis_login` — HEMIS API login field (student_id_number/employee login)
        - `email` — optional (partial unique index — faqat NOT NULL qatorlar)
        - `pinfl` — profiles tablesida (passport PIN, milliy ID)
    """

    __tablename__ = "users"
    __table_args__ = (
        # Email partial unique — faqat NOT NULL qatorlar uchun
        Index(
            "ux_users_email_notnull", "email", unique=True,
            postgresql_where=text("email IS NOT NULL"),
        ),
    )

    # Phase 10b — email endi optional. Partial unique index above.
    email: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, index=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_2fa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    totp_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)

    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_ip: Mapped[str | None] = mapped_column(INET, nullable=True)

    tenant_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("organizations.id", ondelete="SET NULL"), index=True, nullable=True
    )

    # ========================================================================
    # Phase 10b — HEMIS identity (talaba/o'qituvchi uchun)
    # ========================================================================
    # HEMIS primary ID — Student/Employee `id` field. Unique per OTM.
    hemis_id: Mapped[int | None] = mapped_column(
        BigInteger, unique=True, index=True, nullable=True
    )
    # HEMIS API auth login field. Student'da `student_id_number`, employee'da xodim login.
    hemis_login: Mapped[str | None] = mapped_column(
        String(50), unique=True, index=True, nullable=True
    )
    # HEMIS data drift detection — SHA256 of sorted JSON
    hemis_data_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hemis_last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ========================================================================
    # Talaba-only fields (HEMIS Student schema'dan)
    # ========================================================================
    group_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("academic_groups.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    current_semester_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 'fulltime' | 'parttime' | 'evening' | 'distance' — HEMIS educationForm.code
    education_form: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # 'contract' | 'grand' | 'state' — HEMIS paymentForm.code
    payment_form: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # 'active' | 'academic_leave' | 'graduated' | 'expelled' — HEMIS studentStatus.code
    student_status: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # ========================================================================
    # O'qituvchi/xodim-only fields (HEMIS Employee'dan)
    # ========================================================================
    # 'rector' | 'dean' | 'teacher' | 'admin' — HEMIS staffPosition
    staff_position: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # 'primary' | 'secondary' | 'hourly' — HEMIS employmentForm
    employment_form: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # '1.0' | '0.5' | '0.25' — HEMIS employmentStaff
    employment_staff: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Relationships (string refs to avoid import cycles)
    profile: Mapped["Profile | None"] = relationship(  # type: ignore[name-defined]
        "Profile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    user_roles: Mapped[list["UserRole"]] = relationship(  # type: ignore[name-defined]
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="UserRole.user_id",
        primaryjoin="User.id == UserRole.user_id",
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class Profile(Base, TimestampMixin):
    """Foydalanuvchi profil ma'lumotlari — passport, manzil, til, HEMIS ekstra fieldlar.

    Phase 10b — yangi field'lar HEMIS Student schema'dan keladi:
        - first_name/last_name/middle_name — alohida saqlanadi (full_name'dan parsing emas)
        - country/region/district — HEMIS Classifier
        - social_category/poverty_level/accommodation — HEMIS classifier
        - academic_degree/academic_title — faqat xodim/o'qituvchi
    """

    __tablename__ = "profiles"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Phase 10b — alohida name fieldlar HEMIS sync uchun
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    middle_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    pinfl: Mapped[str | None] = mapped_column(String(14), unique=True, nullable=True)
    passport_series: Mapped[str | None] = mapped_column(String(2), nullable=True)
    passport_number: Mapped[str | None] = mapped_column(String(7), nullable=True)
    birthdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Phase 10b — manzil ierarxiyasi (HEMIS Classifier code)
    country: Mapped[str | None] = mapped_column(String(50), nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Phase 10b — ijtimoiy klassifikatsiyalar
    social_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    poverty_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    accommodation: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Phase 10b — xodim/o'qituvchi akademik darajalar
    academic_degree: Mapped[str | None] = mapped_column(String(50), nullable=True)
    academic_title: Mapped[str | None] = mapped_column(String(50), nullable=True)

    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="uz-lat", nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Tashkent", nullable=False)
    notification_preferences: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="profile")

    def __repr__(self) -> str:
        return f"<Profile user_id={self.user_id}>"

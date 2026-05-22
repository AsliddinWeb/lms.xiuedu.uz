"""Users Pydantic schemalar (admin CRUD uchun)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _validate_password_optional(v: str | None) -> str | None:
    if v is None:
        return None
    if len(v) < 10:
        raise ValueError("Parol kamida 10 belgi bo'lishi kerak")
    if not any(c.isupper() for c in v):
        raise ValueError("Parolda kamida 1 ta katta harf bo'lishi kerak")
    if not any(c.isdigit() for c in v):
        raise ValueError("Parolda kamida 1 ta raqam bo'lishi kerak")
    if not any(c in "!@#$%^&*()_+-=[]{};:'\",.<>/?\\|`~" for c in v):
        raise ValueError("Parolda kamida 1 ta maxsus belgi bo'lishi kerak")
    return v


# ---------- Request ----------


class UserCreateRequest(BaseModel):
    """Foydalanuvchi yaratish so'rovi.

    Phase 10b — `email` optional. Lokal staff/admin uchun email kerak,
    HEMIS talaba/o'qituvchi uchun `hemis_login` ishlatiladi. Lekin password
    har holda majburiy (HEMIS user'lar kelajakda HEMIS API orqali kirishadi).
    """

    email: EmailStr | None = None
    password: str = Field(min_length=10, max_length=100)
    full_name: str = Field(min_length=2, max_length=200)
    phone: str | None = Field(default=None, max_length=20)
    is_active: bool = True
    is_verified: bool = False
    tenant_id: int | None = None
    role_codes: list[str] = Field(default_factory=list)
    # Phase 10b — HEMIS identifier (agar admin manual HEMIS user yaratsa)
    hemis_id: int | None = None
    hemis_login: str | None = Field(default=None, max_length=50)

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        result = _validate_password_optional(v)
        assert result is not None
        return result


class UserUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    phone: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None
    is_verified: bool | None = None
    tenant_id: int | None = None
    avatar_url: str | None = None


class UserSetPasswordRequest(BaseModel):
    password: str = Field(min_length=10, max_length=100)

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        result = _validate_password_optional(v)
        assert result is not None
        return result


# ---------- Response ----------


class UserListItem(BaseModel):
    id: int
    # Phase 10b — email endi optional (HEMIS-only foydalanuvchilarda yo'q)
    email: EmailStr | None = None
    full_name: str
    phone: str | None
    avatar_url: str | None
    is_active: bool
    is_verified: bool
    is_2fa_enabled: bool
    last_login_at: datetime | None
    tenant_id: int | None
    # Phase 10b — HEMIS identifierlari ro'yxat ko'rinishda
    hemis_id: int | None = None
    hemis_login: str | None = None
    roles: list[str] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserDetail(UserListItem):
    permissions: list[str] = Field(default_factory=list)


class PaginatedUsers(BaseModel):
    items: list[UserListItem]
    total: int
    page: int
    page_size: int


# ============================================================================
# Profile (Phase 2c) — talabaning shaxsiy va akademik ma'lumotlari
# ============================================================================


class ProfilePublic(BaseModel):
    # Phase 10b — alohida ism komponentlari (HEMIS sync uchun)
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None

    pinfl: str | None = None
    passport_series: str | None = None
    passport_number: str | None = None
    birthdate: str | None = None  # ISO date string
    gender: str | None = None
    nationality: str | None = None
    address: str | None = None

    # Phase 10b — manzil ierarxiyasi (HEMIS Classifier code)
    country: str | None = None
    region: str | None = None
    district: str | None = None

    # Phase 10b — ijtimoiy klassifikatsiya
    social_category: str | None = None
    poverty_level: str | None = None
    accommodation: str | None = None

    # Phase 10b — o'qituvchi/xodim akademik darajalar
    academic_degree: str | None = None
    academic_title: str | None = None

    bio: str | None = None
    language: str = "uz-lat"
    timezone: str = "Asia/Tashkent"
    notification_preferences: dict = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class MeResponse(BaseModel):
    """Joriy foydalanuvchi: user + profile + roles + permissions.

    Phase 10b — email optional, HEMIS identifierlar va talaba/xodim metadata.
    """

    id: int
    email: EmailStr | None = None
    full_name: str
    phone: str | None
    avatar_url: str | None
    is_active: bool
    is_verified: bool
    is_2fa_enabled: bool
    last_login_at: datetime | None
    tenant_id: int | None

    # Phase 10b — HEMIS identity
    hemis_id: int | None = None
    hemis_login: str | None = None
    hemis_last_synced_at: datetime | None = None

    # Phase 10b — talaba metadata (HEMIS Student'dan)
    group_id: int | None = None
    current_semester_id: int | None = None
    education_form: str | None = None
    payment_form: str | None = None
    student_status: str | None = None

    # Phase 10b — xodim metadata (HEMIS Employee'dan)
    staff_position: str | None = None
    employment_form: str | None = None
    employment_staff: str | None = None

    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    profile: ProfilePublic | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MeUpdateRequest(BaseModel):
    """Foydalanuvchi o'zining profil ma'lumotlarini yangilashi."""

    # User-level
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    # Phone E.164-ga moslashgan: +998901234567 yoki bo'sh
    phone: str | None = Field(default=None, max_length=20, pattern=r"^\+?[0-9]{7,19}$")

    # Profile-level
    # PINFL — 14 raqam (O'zbekiston JShShIR)
    pinfl: str | None = Field(default=None, pattern=r"^\d{14}$")
    # Passport series: 2 lotin katta harf
    passport_series: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    # Passport number: 7 raqam
    passport_number: str | None = Field(default=None, pattern=r"^\d{7}$")
    birthdate: str | None = None  # YYYY-MM-DD (validatsiya endpointda)
    gender: str | None = Field(default=None, max_length=10)
    nationality: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=500)
    bio: str | None = Field(default=None, max_length=1000)
    language: str | None = Field(default=None, max_length=10)
    timezone: str | None = Field(default=None, max_length=50)


class MePreferencesRequest(BaseModel):
    """notification_preferences JSONB to'liq replace."""

    notification_preferences: dict = Field(default_factory=dict)


class AvatarResponse(BaseModel):
    avatar_url: str

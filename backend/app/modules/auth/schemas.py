"""Auth Pydantic schemas (request/response).

Spec: docs/03-modules/01-auth.md
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from pydantic.networks import IPvAnyAddress

# ---------- Parol qoidalari ----------


def _validate_password(v: str) -> str:
    if not any(c.isupper() for c in v):
        raise ValueError("Parolda kamida 1 ta katta harf bo'lishi kerak")
    if not any(c.isdigit() for c in v):
        raise ValueError("Parolda kamida 1 ta raqam bo'lishi kerak")
    if not any(c in "!@#$%^&*()_+-=[]{};:'\",.<>/?\\|`~" for c in v):
        raise ValueError("Parolda kamida 1 ta maxsus belgi bo'lishi kerak")
    return v


# ---------- Request ----------


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=100)
    full_name: str = Field(min_length=2, max_length=200)
    phone: str | None = Field(default=None, max_length=20)

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return _validate_password(v)


class LoginRequest(BaseModel):
    email: EmailStr | None = None
    phone: str | None = None
    password: str = Field(min_length=1)
    # 6 raqamli TOTP yoki 9 belgili backup code (4-4 format: "abcd-1234")
    totp_code: str | None = Field(default=None, min_length=6, max_length=16)

    @field_validator("phone")
    @classmethod
    def _normalize_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return v.strip().replace(" ", "")


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=10, max_length=100)

    @field_validator("new_password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return _validate_password(v)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10)
    new_password: str = Field(min_length=10, max_length=100)

    @field_validator("new_password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return _validate_password(v)


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=10)


class TwoFactorSetupResponse(BaseModel):
    secret: str
    otpauth_uri: str
    qr_png_base64: str


class TwoFactorVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=8)


class TwoFactorEnableResponse(BaseModel):
    backup_codes: list[str]


class TwoFactorDisableRequest(BaseModel):
    password: str = Field(min_length=1)
    code: str = Field(min_length=6, max_length=8)


class BackupCodesResponse(BaseModel):
    backup_codes: list[str]


class HemisLoginRequest(BaseModel):
    """HEMIS login + parol — bizning backend HEMIS API ga forward qiladi."""

    login: str = Field(min_length=1, max_length=64, description="HEMIS login (talaba ID raqam)")
    password: str = Field(min_length=1)


class HemisSsoCallbackRequest(BaseModel):
    """Phase 10e — HEMIS SSO callback payload.

    Talaba HEMIS portalida login bo'lib, "LMS'ga o'tish" tugmasini bossa,
    HEMIS bizga `?sso_token=...` bilan redirect qiladi. Frontend tokenni
    backend'ga POST qiladi.

    Token muddati ~300 sekund (HEMIS `expires_in` qaytaradi).
    """

    sso_token: str = Field(
        min_length=10, max_length=2048, description="HEMIS SSO short-lived token"
    )


class HemisTutorLoginRequest(BaseModel):
    """Phase 10g — HEMIS pedagog (tutor) login.

    HEMIS tutor login reCAPTCHA bilan himoyalangan. Frontend Google
    reCAPTCHA v3 token'ni `recaptcha` field'ida yuboradi.
    """

    login: str = Field(min_length=1, max_length=64, description="HEMIS tutor login")
    password: str = Field(min_length=1)
    recaptcha: str = Field(
        min_length=1, max_length=2048, description="Google reCAPTCHA v3 token"
    )


# ---------- Response ----------


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserPublic(BaseModel):
    """Maxfiy bo'lmagan user ma'lumotlari (frontendga yuboriladi).

    Phase 10b — email optional (HEMIS-only foydalanuvchilarda yo'q bo'lishi mumkin).
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
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class SessionPublic(BaseModel):
    id: int
    ip_address: IPvAnyAddress | None
    user_agent: str | None
    device_info: dict
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- Internal ----------


class AuthContext(BaseModel):
    """Login/Register oqimini IP+UA bilan boyitish uchun internal DTO."""

    ip_address: str
    user_agent: str | None = None

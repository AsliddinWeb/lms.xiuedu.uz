"""Auth-specific xatoliklar."""

from fastapi import status

from app.core.exceptions import AppException


class UserAlreadyExistsError(AppException):
    def __init__(self) -> None:
        super().__init__(
            "Bu email bilan foydalanuvchi mavjud", status.HTTP_409_CONFLICT, "user_exists"
        )


class InvalidCredentialsError(AppException):
    def __init__(self) -> None:
        super().__init__(
            "Email yoki parol noto'g'ri", status.HTTP_401_UNAUTHORIZED, "invalid_credentials"
        )


class AccountLockedError(AppException):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(
            f"Akkaunt vaqtincha bloklangan. {retry_after_seconds}s kuting.",
            status.HTTP_423_LOCKED,
            "account_locked",
        )


class AccountDisabledError(AppException):
    def __init__(self) -> None:
        super().__init__(
            "Akkaunt o'chirilgan", status.HTTP_403_FORBIDDEN, "account_disabled"
        )


class TwoFactorRequiredError(AppException):
    def __init__(self) -> None:
        super().__init__(
            "2FA kod talab qilinadi", status.HTTP_401_UNAUTHORIZED, "two_factor_required"
        )


class InvalidTotpError(AppException):
    def __init__(self) -> None:
        super().__init__(
            "Noto'g'ri 2FA kod", status.HTTP_401_UNAUTHORIZED, "invalid_totp"
        )


class InvalidTokenError(AppException):
    def __init__(self, detail: str = "Token yaroqsiz yoki muddati o'tgan") -> None:
        super().__init__(detail, status.HTTP_401_UNAUTHORIZED, "invalid_token")


class SessionRevokedError(AppException):
    def __init__(self) -> None:
        super().__init__(
            "Sessiya bekor qilingan", status.HTTP_401_UNAUTHORIZED, "session_revoked"
        )

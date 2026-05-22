from fastapi import HTTPException, status


class AppException(HTTPException):
    """Loyihada qo'llaniladigan asosiy xatolik klassi."""

    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: str = "app_error",
    ) -> None:
        super().__init__(status_code=status_code, detail=detail)
        self.code = code


class NotFoundError(AppException):
    def __init__(self, detail: str = "Resurs topilmadi") -> None:
        super().__init__(detail, status.HTTP_404_NOT_FOUND, "not_found")


class UnauthorizedError(AppException):
    def __init__(self, detail: str = "Autentifikatsiya talab qilinadi") -> None:
        super().__init__(detail, status.HTTP_401_UNAUTHORIZED, "unauthorized")


class ForbiddenError(AppException):
    def __init__(self, detail: str = "Ruxsat yo'q") -> None:
        super().__init__(detail, status.HTTP_403_FORBIDDEN, "forbidden")


class ConflictError(AppException):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, status.HTTP_409_CONFLICT, "conflict")


class ValidationError(AppException):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, status.HTTP_422_UNPROCESSABLE_ENTITY, "validation_error")

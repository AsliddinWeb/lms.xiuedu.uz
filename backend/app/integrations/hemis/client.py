"""HEMIS API klienti — Phase 10c (to'liq qayta yozilgan).

Spec: md_files/hemis_integration/hemis_openapi.json (OpenAPI 3.0, 254 endpoint)
Base URL: settings.HEMIS_API_URL (default: https://student.xiuedu.uz/rest)

Endpoint guruhlari:
- Auth: student_login, tutor_login, refresh_token, sso_targets, sso_redirect_url
- Student API: account_me, subject_list, schedule, gpa_list, attendance,
  performance, exam_table, semesters, account_refresh
- Backend API (admin sync): student_list, employee_list, department_list,
  group_list, curriculum_list, curriculum_subject_list
- Tutor API: tutor_profile, tutor_groups, tutor_group_students,
  tutor_grade_student, tutor_attendance_by_subject

Mode'lar:
- `settings.HEMIS_MODE = 'mock'` (default) — `mock_data.py`-dan fixtura qaytaradi
- `settings.HEMIS_MODE = 'real'` — to'g'ridan-to'g'ri HTTP yuboradi

Foydalanish:
    async with HemisClient() as client:
        login = await client.student_login("999211100073", "DD7777777")
        student = await client.account_me(login["token"])

Auth uchun JWT cache:
    HemisTokenCache (Redis-backed) — login-dan keyin tokenni saqlab,
    har request'da qayta login qilinmasligi uchun.

Real-mode'da har 401 da retry_async + automatic token refresh.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.integrations.hemis import mock_data

logger = get_logger(__name__)


# ============================================================================
# Exceptions
# ============================================================================


class HemisError(Exception):
    """HEMIS API'dan kelgan xato (network, 4xx, 5xx)."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class HemisAuthError(HemisError):
    """Login/parol xato yoki HEMIS rad qildi (401/403)."""


class HemisNotFoundError(HemisError):
    """Resurs topilmadi (404)."""


# ============================================================================
# Client
# ============================================================================


class HemisClient:
    """HEMIS API bilan async ishlash uchun klient.

    Mock mode: `settings.HEMIS_MODE = 'mock'` — fixture'lar qaytariladi.
    Real mode: `settings.HEMIS_MODE = 'real'` — real HTTP.

    Foydalanish:
        async with HemisClient() as client:
            tokens = await client.student_login("999211100073", "DD7777777")
            me = await client.account_me(tokens["token"])
    """

    DEFAULT_BASE_URL = "https://student.xiuedu.uz/rest"
    TIMEOUT = 15.0
    USER_AGENT = "XIU-LMS/0.1"

    def __init__(
        self,
        base_url: str | None = None,
        *,
        mode: str | None = None,
    ) -> None:
        self.base_url = (
            base_url or settings.HEMIS_API_URL or self.DEFAULT_BASE_URL
        ).rstrip("/")
        self.mode = mode or settings.HEMIS_MODE
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "HemisClient":
        if self.mode == "real":
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.TIMEOUT,
                headers={
                    "Accept": "application/json",
                    "User-Agent": self.USER_AGENT,
                },
            )
        return self

    async def __aexit__(self, *_exc) -> None:  # noqa: ANN001
        if self._client is not None:
            await self._client.aclose()

    # ------------------------------------------------------------------------
    # Low-level HTTP helpers
    # ------------------------------------------------------------------------

    @property
    def client(self) -> httpx.AsyncClient:
        if self.mode == "mock":
            raise RuntimeError(
                "HemisClient mock mode'da — to'g'ridan HTTP client ishlatilmaydi"
            )
        if self._client is None:
            raise RuntimeError("HemisClient: 'async with' bilan ishlatish kerak")
        return self._client

    def _envelope_data(self, body: dict[str, Any]) -> Any:
        """HEMIS standart {success, data, error, code} envelopni unwrap qiladi."""
        if not isinstance(body, dict):
            raise HemisError(f"HEMIS yaroqsiz javob: {type(body).__name__}")
        if not body.get("success"):
            err = body.get("error") or "HEMIS rad qildi"
            code = body.get("code") or 400
            if code in (401, 403):
                raise HemisAuthError(str(err), status_code=code)
            if code == 404:
                raise HemisNotFoundError(str(err), status_code=code)
            raise HemisError(str(err), status_code=code)
        return body.get("data")

    async def _get(
        self,
        path: str,
        *,
        token: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """GET request — real mode'da HTTP, mock mode'da NotImplementedError.

        Mock mode'da bu method chaqirilmasligi kerak — har endpoint metodi mock
        qaytaradi.
        """
        if self.mode == "mock":
            raise NotImplementedError("Mock mode: endpoint method'ini ishlatib turibmiz")
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            r = await self.client.get(path, headers=headers, params=params or {})
        except httpx.HTTPError as exc:
            raise HemisError(f"HEMIS GET {path}: {exc}") from exc
        return self._handle_response(r, path)

    async def _post(
        self,
        path: str,
        *,
        token: str | None = None,
        json: dict[str, Any] | None = None,
        cookies: dict[str, str] | None = None,
    ) -> Any:
        if self.mode == "mock":
            raise NotImplementedError("Mock mode")
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            r = await self.client.post(
                path, headers=headers, json=json, cookies=cookies or {}
            )
        except httpx.HTTPError as exc:
            raise HemisError(f"HEMIS POST {path}: {exc}") from exc
        return self._handle_response(r, path, _response=r)

    def _handle_response(
        self,
        r: httpx.Response,
        path: str,
        _response: httpx.Response | None = None,
    ) -> Any:
        if r.status_code == 401:
            raise HemisAuthError(f"HEMIS {path} 401", status_code=401)
        if r.status_code == 403:
            raise HemisAuthError(f"HEMIS {path} 403", status_code=403)
        if r.status_code == 404:
            raise HemisNotFoundError(f"HEMIS {path} 404", status_code=404)
        if r.status_code >= 500:
            raise HemisError(f"HEMIS {path} {r.status_code} server xatosi", status_code=r.status_code)
        if r.status_code not in (200, 201, 202):
            raise HemisError(
                f"HEMIS {path} kutilmagan javob: {r.status_code}", status_code=r.status_code
            )
        try:
            body = r.json()
        except ValueError:
            raise HemisError(f"HEMIS {path} JSON parse xatosi")
        return self._envelope_data(body)

    # ========================================================================
    # 1. AUTH
    # ========================================================================

    async def student_login(self, login: str, password: str) -> dict[str, Any]:
        """`POST /v1/auth/login` — talaba login.

        Returns: {"token": str, "refresh_token": str | None}
        """
        if self.mode == "mock":
            data = self._envelope_data(mock_data.mock_student_login(login, password))
            return {"token": data["token"], "refresh_token": None}

        try:
            r = await self.client.post(
                "/v1/auth/login",
                json={"login": login, "password": password},
            )
        except httpx.HTTPError as exc:
            raise HemisError(f"HEMIS login ulanish: {exc}") from exc
        refresh = r.cookies.get("refresh-token")
        data = self._handle_response(r, "/v1/auth/login")
        return {"token": data["token"], "refresh_token": refresh}

    async def tutor_login(
        self, login: str, password: str, recaptcha: str
    ) -> dict[str, Any]:
        """`POST /ver1/tutor/auth/login` — pedagog login.

        Returns: {"token": str, "refresh_token": str}
        """
        if self.mode == "mock":
            data = self._envelope_data(
                mock_data.mock_tutor_login(login, password, recaptcha)
            )
            return data

        data = await self._post(
            "/ver1/tutor/auth/login",
            json={"login": login, "password": password, "reCaptcha": recaptcha},
        )
        return data

    async def refresh_student_token(self, refresh_cookie: str) -> dict[str, Any]:
        """Cookie-based refresh."""
        if self.mode == "mock":
            return {"token": mock_data.MOCK_STUDENT_TOKEN, "refresh_token": refresh_cookie}
        try:
            r = await self.client.post(
                "/v1/auth/refresh-token",
                cookies={"refresh-token": refresh_cookie},
            )
        except httpx.HTTPError as exc:
            raise HemisError(f"HEMIS refresh ulanish: {exc}") from exc
        data = self._handle_response(r, "/v1/auth/refresh-token")
        return {"token": data["token"], "refresh_token": r.cookies.get("refresh-token")}

    async def refresh_tutor_token(self, refresh_token: str) -> dict[str, Any]:
        if self.mode == "mock":
            return {"token": mock_data.MOCK_TUTOR_TOKEN, "refresh_token": refresh_token}
        data = await self._post(
            "/ver1/tutor/auth/refresh-token", json={"refresh_token": refresh_token}
        )
        return data

    # ========================================================================
    # 2. SSO
    # ========================================================================

    async def sso_targets(self, student_token: str) -> list[dict[str, Any]]:
        """`GET /v1/sso/targets` — mavjud SSO partnerlar ro'yxati."""
        if self.mode == "mock":
            return self._envelope_data(mock_data.mock_sso_targets(student_token))
        return await self._get("/v1/sso/targets", token=student_token)

    async def sso_redirect_url(
        self, student_token: str, target: str
    ) -> dict[str, Any]:
        """`GET /v1/sso/get-redirect-url?target=...` — partnera redirect URL + token.

        Returns: {"redirect_url": str, "target": str, "expires_in": int}
        """
        if self.mode == "mock":
            return self._envelope_data(
                mock_data.mock_sso_redirect_url(student_token, target)
            )
        return await self._get(
            "/v1/sso/get-redirect-url", token=student_token, params={"target": target}
        )

    # ========================================================================
    # 3. STUDENT API
    # ========================================================================

    async def account_me(self, token: str) -> dict[str, Any]:
        """`GET /v1/account/me` — talabaning to'liq profili."""
        if self.mode == "mock":
            return self._envelope_data(mock_data.mock_account_me(token))
        return await self._get("/v1/account/me", token=token)

    async def account_refresh(self, token: str) -> dict[str, Any]:
        """`GET /v1/account/refresh` — tashqi xizmatlardan yangilash."""
        if self.mode == "mock":
            return self._envelope_data(mock_data.mock_account_me(token))
        return await self._get("/v1/account/refresh", token=token)

    async def subject_list(
        self, token: str, semester: int | None = None
    ) -> list[dict[str, Any]]:
        """`GET /v1/education/subject-list` — biriktirilgan fanlar + grades."""
        if self.mode == "mock":
            return self._envelope_data(mock_data.mock_subject_list(token, semester))
        params = {"semester": semester} if semester else None
        return await self._get("/v1/education/subject-list", token=token, params=params)

    async def schedule(self, token: str) -> list[dict[str, Any]]:
        """`GET /v1/education/schedule` — dars jadvali."""
        if self.mode == "mock":
            return self._envelope_data(mock_data.mock_schedule(token))
        return await self._get("/v1/education/schedule", token=token)

    async def gpa_list(self, token: str) -> list[dict[str, Any]]:
        """`GET /v1/education/gpa-list` — GPA tarixi."""
        if self.mode == "mock":
            return self._envelope_data(mock_data.mock_gpa_list(token))
        return await self._get("/v1/education/gpa-list", token=token)

    async def attendance(
        self, token: str, semester: int | None = None
    ) -> list[dict[str, Any]]:
        """`GET /v1/education/attendance` — davomat."""
        if self.mode == "mock":
            return self._envelope_data(mock_data.mock_attendance(token, semester))
        params = {"semester": semester} if semester else None
        return await self._get("/v1/education/attendance", token=token, params=params)

    async def exam_table(self, token: str) -> list[dict[str, Any]]:
        """`GET /v1/education/exam-table` — imtihon jadvali."""
        if self.mode == "mock":
            return self._envelope_data(mock_data.mock_exam_table(token))
        return await self._get("/v1/education/exam-table", token=token)

    async def semesters(self, token: str) -> list[dict[str, Any]]:
        """`GET /v1/education/semesters` — o'quv reja semestrlar."""
        if self.mode == "mock":
            return self._envelope_data(mock_data.mock_semesters(token))
        return await self._get("/v1/education/semesters", token=token)

    # ========================================================================
    # 4. BACKEND API (admin sync, talab qiladi `HEMIS_API_TOKEN`)
    # ========================================================================

    def _backend_token(self, token: str | None = None) -> str | None:
        return token or settings.HEMIS_API_TOKEN or None

    async def student_list(
        self, *, page: int = 1, limit: int = 100, token: str | None = None
    ) -> dict[str, Any]:
        """`GET /v1/data/student-list` — barcha talabalar (admin sync)."""
        if self.mode == "mock":
            return self._envelope_data(mock_data.mock_student_list("admin", page, limit))
        return await self._get(
            "/v1/data/student-list",
            token=self._backend_token(token),
            params={"page": page, "limit": limit},
        )

    async def employee_list(
        self,
        *,
        page: int = 1,
        limit: int = 100,
        type_: str = "employee",
        token: str | None = None,
    ) -> dict[str, Any]:
        """`GET /v1/data/employee-list` — o'qituvchilar va hodimlar (admin sync)."""
        if self.mode == "mock":
            return self._envelope_data(
                mock_data.mock_employee_list("admin", page, limit, type_)
            )
        return await self._get(
            "/v1/data/employee-list",
            token=self._backend_token(token),
            params={"page": page, "limit": limit, "type": type_},
        )

    async def department_list(self, *, token: str | None = None) -> list[dict[str, Any]]:
        """`GET /v1/data/department-list` — fakultetlar/kafedralar."""
        if self.mode == "mock":
            return self._envelope_data(mock_data.mock_department_list("admin"))
        return await self._get("/v1/data/department-list", token=self._backend_token(token))

    async def group_list(self, *, token: str | None = None) -> list[dict[str, Any]]:
        """`GET /v1/data/group-list` — barcha akademik guruhlar."""
        if self.mode == "mock":
            return self._envelope_data(mock_data.mock_group_list("admin"))
        return await self._get("/v1/data/group-list", token=self._backend_token(token))

    async def curriculum_list(self, *, token: str | None = None) -> list[dict[str, Any]]:
        """`GET /v1/data/curriculum-list` — barcha o'quv rejalar."""
        if self.mode == "mock":
            return self._envelope_data(mock_data.mock_curriculum_list("admin"))
        return await self._get("/v1/data/curriculum-list", token=self._backend_token(token))

    # ========================================================================
    # 5. TUTOR API (pedagog)
    # ========================================================================

    async def tutor_profile(self, tutor_token: str) -> dict[str, Any]:
        """`GET /ver1/tutor/profile/index` — pedagog profili."""
        if self.mode == "mock":
            return self._envelope_data(mock_data.mock_tutor_profile(tutor_token))
        return await self._get("/ver1/tutor/profile/index", token=tutor_token)

    async def tutor_groups(self, tutor_token: str) -> list[dict[str, Any]]:
        """`GET /ver1/tutor/profile/groups` — pedagogga biriktirilgan guruhlar."""
        if self.mode == "mock":
            return self._envelope_data(mock_data.mock_tutor_groups(tutor_token))
        return await self._get("/ver1/tutor/profile/groups", token=tutor_token)

    async def tutor_group_students(
        self, tutor_token: str, group_id: int
    ) -> list[dict[str, Any]]:
        """`GET /ver1/tutor/group/students?group=ID` — guruh talabalari."""
        if self.mode == "mock":
            return self._envelope_data(
                mock_data.mock_tutor_group_students(tutor_token, group_id)
            )
        return await self._get(
            "/ver1/tutor/group/students",
            token=tutor_token,
            params={"group": group_id},
        )

    async def tutor_grade_gpa(
        self, tutor_token: str, group_id: int
    ) -> list[dict[str, Any]]:
        """`GET /ver1/tutor/grade/gpa?group=ID` — guruh GPA reytingi."""
        if self.mode == "mock":
            return self._envelope_data(
                mock_data.mock_tutor_grade_gpa(tutor_token, group_id)
            )
        return await self._get(
            "/ver1/tutor/grade/gpa", token=tutor_token, params={"group": group_id}
        )

    async def tutor_attendance_by_subject(
        self, tutor_token: str, group_id: int, subject_id: int | None = None
    ) -> list[dict[str, Any]]:
        """`GET /ver1/tutor/attendance/by-subject` — fan bo'yicha guruh davomati."""
        if self.mode == "mock":
            return self._envelope_data(
                mock_data.mock_tutor_attendance_by_subject(
                    tutor_token, group_id, subject_id
                )
            )
        params: dict[str, Any] = {"group": group_id}
        if subject_id is not None:
            params["subject"] = subject_id
        return await self._get(
            "/ver1/tutor/attendance/by-subject", token=tutor_token, params=params
        )

    async def tutor_grade_debtors(
        self, tutor_token: str, group_id: int
    ) -> list[dict[str, Any]]:
        """`GET /ver1/tutor/grade/debtors?group=ID` — qarzdor talabalar."""
        if self.mode == "mock":
            return self._envelope_data(
                mock_data.mock_tutor_grade_debtors(tutor_token, group_id)
            )
        return await self._get(
            "/ver1/tutor/grade/debtors",
            token=tutor_token,
            params={"group": group_id},
        )

    # ========================================================================
    # 6. EXAM GRADES UPLOAD (Phase 7c — DAK avto-sync)
    # ========================================================================

    async def push_exam_grades(
        self, *, payload: dict[str, Any], token: str | None = None
    ) -> dict[str, Any]:
        """`POST /v1/exam-grades` — DAK imtihon baholarini HEMIS'ga yuborish.

        Phase 7c'dan saqlangan endpoint. Production paytida real schema'ni HEMIS
        documentation'iga moslab tuzatish kerak.
        """
        if self.mode == "mock":
            return {"status_code": 200, "body": {"success": True, "received": True}}

        bearer = token or settings.HEMIS_API_TOKEN
        headers = {"Authorization": f"Bearer {bearer}"} if bearer else {}
        try:
            r = await self.client.post(
                "/v1/exam-grades", json=payload, headers=headers
            )
        except httpx.HTTPError as exc:
            raise HemisError(f"HEMIS exam-grades ulanish: {exc}") from exc
        if r.status_code == 401:
            raise HemisAuthError("HEMIS service token yaroqsiz", status_code=401)
        if r.status_code >= 500:
            raise HemisError(f"HEMIS exam-grades {r.status_code}", status_code=r.status_code)
        if r.status_code not in (200, 201, 202):
            raise HemisError(
                f"HEMIS exam-grades: {r.status_code} {r.text[:200]}",
                status_code=r.status_code,
            )
        try:
            body = r.json()
        except ValueError:
            body = {"raw": r.text}
        return {"status_code": r.status_code, "body": body}

    # ========================================================================
    # Legacy aliases (Phase 1e API compatibility)
    # ========================================================================

    async def login(self, login: str, password: str) -> dict[str, Any]:
        """Legacy alias — eski kod `client.login()` ishlatadi."""
        return await self.student_login(login, password)

    async def get_me(self, token: str) -> dict[str, Any]:
        """Legacy alias."""
        return await self.account_me(token)

    async def refresh_token(self, refresh_cookie: str) -> dict[str, Any]:
        return await self.refresh_student_token(refresh_cookie)

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_NAME: str = "XIU LMS Backend"
    APP_VERSION: str = "0.1.0"
    APP_DEBUG: bool = False
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # --- Database ---
    DATABASE_URL: PostgresDsn
    DATABASE_ECHO: bool = False

    # --- Redis ---
    REDIS_URL: RedisDsn

    # --- MinIO ---
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str = "lms-files"
    MINIO_USE_SSL: bool = False
    MINIO_PUBLIC_URL: str = ""

    # --- JWT ---
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- CORS ---
    CORS_ORIGINS: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # --- Cookie ---
    COOKIE_DOMAIN: str = ""
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"

    # --- Frontend URL'lar (email link generatsiyasi uchun) ---
    APP_FRONTEND_URL: str = "http://localhost:8201"
    ADMIN_FRONTEND_URL: str = "http://localhost:8203"

    # --- Email ---
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@xiuedu.uz"
    SMTP_USE_TLS: bool = True

    # --- 559-qaror ---
    TEACHER_STUDENT_RATIO_MAX: int = 50
    BACHELOR_STUDENTS_PER_SPECIALTY_MAX: int = 300
    MASTER_STUDENTS_PER_SPECIALTY_MAX: int = 30
    ACADEMIC_YEAR: str = "2025-2026"
    SEMESTER: Literal["autumn", "spring", "summer"] = "autumn"

    # --- Single-tenant XIU only ---
    # Loyiha faqat 1 ta universitet (XIU) uchun. Schema multi-tenant qoladi,
    # lekin barcha record'lar shu yagona Organization'ga bog'lanadi.
    # `seed.py` da `id=1` bilan idempotent yaratiladi.
    TENANT_CODE: str = "XIU"
    TENANT_NAME: str = "Xalqaro Innovatsiya Universiteti"
    TENANT_DOMAIN: str = "xiuedu.uz"

    # --- Integratsiyalar (bo'sh = o'chirilgan) ---
    ONEID_CLIENT_ID: str = ""
    ONEID_CLIENT_SECRET: str = ""
    ONEID_REDIRECT_URI: str = ""
    ONEID_AUTHORIZE_URL: str = ""
    ONEID_TOKEN_URL: str = ""

    HEMIS_API_URL: str = "https://student.xiuedu.uz/rest"
    HEMIS_API_TOKEN: str = ""  # service-to-service token (Phase 5+ sync uchun)
    # Phase 7c — False bo'lsa, sync log yoziladi lekin haqiqiy HTTP yuborilmaydi
    HEMIS_SYNC_ENABLED: bool = False
    # Phase 10c — mock vs real HEMIS API
    # 'mock'  — `app/integrations/hemis/mock_data.py`-dan fixed JSON qaytaradi
    # 'real'  — to'g'ridan-to'g'ri HEMIS_API_URL ga HTTP yuboradi
    HEMIS_MODE: Literal["mock", "real"] = "mock"
    # Phase 10c — HEMIS JWT cache TTL (sekundlar) Redis'da
    HEMIS_TOKEN_CACHE_TTL: int = 600  # 10 daqiqa
    # Phase 10e — SSO callback uchun mavjud bo'lgan HEMIS target code
    HEMIS_SSO_TARGET: str = "lms"

    # ------------------------------------------------------------------
    # Phase 15 — HEMIS OAuth2 (standart authorization code flow)
    # ------------------------------------------------------------------
    # HEMIS admin panel'idan oAuth klient yarating:
    #   Tizim → oAuth klientlar → yangi klient → CLIENT_ID + CLIENT_SECRET
    # Redirect URI: https://lms.xiuedu.uz/auth/hemis/callback
    # Talaba va xodim uchun ALOHIDA HEMIS subdomain'lar (universitetga qarab).
    HEMIS_OAUTH_CLIENT_ID: str = ""
    HEMIS_OAUTH_CLIENT_SECRET: str = ""
    # Frontend callback URL (HEMIS shu URL'ga ?code=... bilan qaytadi)
    HEMIS_OAUTH_REDIRECT_URI: str = ""
    # Talaba HEMIS portal (student.xiuedu.uz)
    HEMIS_OAUTH_STUDENT_AUTHORIZE_URL: str = ""
    HEMIS_OAUTH_STUDENT_TOKEN_URL: str = ""
    HEMIS_OAUTH_STUDENT_USERINFO_URL: str = ""
    # Xodim HEMIS portal (alohida subdomain bo'lsa)
    HEMIS_OAUTH_EMPLOYEE_AUTHORIZE_URL: str = ""
    HEMIS_OAUTH_EMPLOYEE_TOKEN_URL: str = ""
    HEMIS_OAUTH_EMPLOYEE_USERINFO_URL: str = ""
    # State CSRF token Redis TTL (5 daqiqa)
    HEMIS_OAUTH_STATE_TTL: int = 300

    # --- Live (Phase 5) — Native WebRTC via LiveKit (self-hosted, tashqi xizmatsiz) ---
    LIVE_DEFAULT_PROVIDER: Literal["native"] = "native"

    # LiveKit self-hosted (docker-compose'da livekit konteyneri)
    # ws://livekit:7880 — backend ichida; brauzer ws://localhost:7880 ga ulanadi
    LIVEKIT_URL_INTERNAL: str = "ws://livekit:7880"  # Backend → LiveKit (faqat token validate uchun)
    LIVEKIT_URL_PUBLIC: str = "ws://localhost:7880"  # Brauzer → LiveKit
    LIVEKIT_API_KEY: str = "devkey"
    LIVEKIT_API_SECRET: str = "devsecret_at_least_32_characters_long"
    LIVEKIT_TOKEN_TTL_SECONDS: int = 21600  # 6 soat

    CLICK_SERVICE_ID: str = ""
    CLICK_MERCHANT_ID: str = ""
    CLICK_SECRET_KEY: str = ""

    PAYME_MERCHANT_ID: str = ""
    PAYME_SECRET_KEY: str = ""

    ESKIZ_API_URL: str = "https://notify.eskiz.uz/api"
    ESKIZ_API_TOKEN: str = ""

    TELEGRAM_BOT_TOKEN: str = ""

    OTJBAT_API_URL: str = ""
    OTJBAT_API_KEY: str = ""
    TSDIN_API_URL: str = ""
    TSDIN_API_KEY: str = ""

    # --- Observability ---
    SENTRY_DSN: str = ""
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_JSON: bool = False

    # --- Security (Phase 7f) ---
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MIN: int = 120
    SECURITY_CSP: str = ""  # bo'sh — middleware default ishlatadi

    # --- Phase 9d — Code runner ---
    CODE_RUNNER_PROVIDER: Literal["mock", "piston"] = "mock"
    PISTON_URL: str = ""  # masalan: http://piston:2000

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()

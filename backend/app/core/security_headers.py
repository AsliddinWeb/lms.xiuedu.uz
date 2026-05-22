"""Security HTTP headers + generic rate limit middleware — Phase 7f.

2 ta middleware:
    1. SecurityHeadersMiddleware — HSTS, X-Frame-Options, X-Content-Type-Options,
       Referrer-Policy, Permissions-Policy, CSP (default — overridable)
    2. RateLimitMiddleware — Redis-based sliding window (per IP), default
       100 req/min. Login va boshqa endpoint'lar uchun module-specific
       rate limit qo'shimcha qoplanadi.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis import redis_client

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 1. Security headers
# ---------------------------------------------------------------------------


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Brauzerga muhim xavfsizlik headers'larini qo'shadi.

    Production'da HSTS yoqiladi (HTTPS majburiy). CSP default:
        - script: self + nonce yo'q (Vue inline'siz ishlaydi)
        - img/font: self + data: (avatar fallback uchun)
        - connect: self + WebSocket (WS uchun ws:///wss://)
        - frame-ancestors: none (clickjacking himoyasi)

    CSP overrideable via settings.SECURITY_CSP — bo'sh bo'lsa default.
    """

    DEFAULT_CSP = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob: https:; "
        "media-src 'self' blob: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' ws: wss: https:; "
        "worker-src 'self' blob:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(self), microphone=(self), display-capture=(self), geolocation=()",
        )
        csp = getattr(settings, "SECURITY_CSP", None) or self.DEFAULT_CSP
        response.headers.setdefault("Content-Security-Policy", csp)
        if settings.is_production:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=63072000; includeSubDomains; preload",
            )
        return response


# ---------------------------------------------------------------------------
# 2. Generic rate limit (Redis sliding window per IP)
# ---------------------------------------------------------------------------


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP sliding window rate limit.

    Sozlamalar:
        RATE_LIMIT_ENABLED        — bool (default True)
        RATE_LIMIT_REQUESTS_PER_MIN — int (default 120)
        RATE_LIMIT_EXEMPT_PATHS   — list[str] (default health/metrics)

    Auth endpoint'larida login attempt rate limit alohida ishlaydi
    (modules/auth/rate_limit.py) — bu middleware umumiy qatlam.
    """

    def __init__(
        self,
        app,
        *,
        requests_per_min: int = 120,
        exempt_prefixes: tuple[str, ...] = ("/metrics", "/api/v1/health", "/docs", "/openapi"),
    ) -> None:
        super().__init__(app)
        self.requests_per_min = requests_per_min
        self.exempt_prefixes = exempt_prefixes
        self.window_seconds = 60

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not getattr(settings, "RATE_LIMIT_ENABLED", True):
            return await call_next(request)

        path = request.url.path
        if any(path.startswith(p) for p in self.exempt_prefixes):
            return await call_next(request)

        ip = self._client_ip(request)
        if not ip:
            return await call_next(request)

        key = f"ratelimit:ip:{ip}"
        try:
            now = int(time.time())
            window_start = now - self.window_seconds

            # Unique member kerak — aks holda bir sekundda bir nechta request
            # bitta zset entry'sini overwrite qiladi.
            member = f"{now}:{uuid.uuid4().hex[:8]}"
            async with redis_client.pipeline(transaction=False) as pipe:
                pipe.zremrangebyscore(key, 0, window_start)
                pipe.zadd(key, {member: now})
                pipe.zcard(key)
                pipe.expire(key, self.window_seconds + 5)
                _, _, count, _ = await pipe.execute()

            limit = self.requests_per_min
            if count > limit:
                logger.warning("rate_limit.exceeded", ip=ip, path=path, count=count)
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Too many requests. Iltimos, biroz kuting.",
                        "retry_after": self.window_seconds,
                    },
                    headers={
                        "Retry-After": str(self.window_seconds),
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                    },
                )
        except Exception:  # noqa: BLE001 — Redis bo'lmasa, oddiy davom etamiz
            logger.exception("rate_limit.error", ip=ip, path=path)

        return await call_next(request)

    @staticmethod
    def _client_ip(request: Request) -> str | None:
        # Reverse proxy bo'lsa, X-Forwarded-For ishlatamiz (ishonchli proxy bo'lsa)
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            return xff.split(",")[0].strip()
        return request.client.host if request.client else None

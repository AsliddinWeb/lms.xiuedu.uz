"""Observability — Phase 7e.

3 ta komponent:
    1. RequestIDMiddleware — har request uchun X-Request-ID generate, structlog'ga bind
    2. Prometheus metrics — `/metrics` endpoint (http_requests_total, latency histogram)
    3. Slow query log — SQLAlchemy event listener (>500ms)
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI
from sqlalchemy import event
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

logger = get_logger(__name__)

SLOW_QUERY_THRESHOLD_MS = 500


# ---------------------------------------------------------------------------
# 1. Request ID middleware
# ---------------------------------------------------------------------------


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Har request uchun X-Request-ID generate qiladi (yoki kelganini ishlatadi).

    structlog `contextvars` ga bind qilinadi — shu request davomidagi har log
    yozuvida `request_id` field bo'ladi.
    """

    HEADER = "X-Request-ID"

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        rid = request.headers.get(self.HEADER) or uuid.uuid4().hex[:16]
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=rid,
            method=request.method,
            path=request.url.path,
        )
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed = (time.perf_counter() - start) * 1000
            logger.exception(
                "http.error",
                duration_ms=round(elapsed, 1),
            )
            raise
        elapsed = (time.perf_counter() - start) * 1000
        response.headers[self.HEADER] = rid
        # 2xx/3xx -> info, 4xx -> warning, 5xx -> error (avval raise bo'ladi)
        log_fn = logger.info
        if 400 <= response.status_code < 500:
            log_fn = logger.warning
        log_fn(
            "http.response",
            status=response.status_code,
            duration_ms=round(elapsed, 1),
        )
        return response


# ---------------------------------------------------------------------------
# 2. Prometheus metrics
# ---------------------------------------------------------------------------


def setup_metrics(app: FastAPI) -> None:
    """`/metrics` endpoint orqali Prometheus scrape qiladi.

    `prometheus-fastapi-instrumentator` paketidan foydalanadi.
    Default metrics:
        http_requests_total{method,handler,status}
        http_request_duration_seconds{method,handler}
    """
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
    except ImportError:
        logger.warning("metrics.disabled", reason="prometheus_fastapi_instrumentator missing")
        return

    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        excluded_handlers=["/metrics", "/api/v1/health"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


# ---------------------------------------------------------------------------
# 3. Slow query detection (SQLAlchemy)
# ---------------------------------------------------------------------------


def setup_slow_query_logging() -> None:
    """SQLAlchemy `before_cursor_execute` + `after_cursor_execute` events.

    Synchronous engine listener — sync DB drivers uchun. Async (asyncpg) bilan
    `sync_engine` orqali ulanadi. >SLOW_QUERY_THRESHOLD_MS bo'lgan query log'ga
    yoziladi.
    """
    from app.core.database import engine

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        context._query_start_time = time.perf_counter()

    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def _after(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        start = getattr(context, "_query_start_time", None)
        if start is None:
            return
        elapsed_ms = (time.perf_counter() - start) * 1000
        if elapsed_ms >= SLOW_QUERY_THRESHOLD_MS:
            logger.warning(
                "db.slow_query",
                duration_ms=round(elapsed_ms, 1),
                statement=str(statement)[:300],
            )

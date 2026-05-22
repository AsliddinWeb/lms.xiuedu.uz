from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.env_validation import validate_production_env
from app.core.observability import (
    RequestIDMiddleware,
    setup_metrics,
    setup_slow_query_logging,
)
from app.core.security_headers import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.redis import redis_client
from app.core.storage import init_storage
from app.db import models as _models  # noqa: F401  # Hamma SQLAlchemy modellarini yuklash
from app.modules.communications.ws_manager import manager as ws_manager

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """App start/stop hook — DB pool, Redis va h.k. uchun."""
    configure_logging()
    logger.info(
        "app.start",
        env=settings.APP_ENV,
        version=settings.APP_VERSION,
    )

    # Phase 7f — production env validation (fail-fast)
    validate_production_env()

    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.APP_ENV,
            release=settings.APP_VERSION,
            traces_sample_rate=0.1,
        )
        logger.info("sentry.initialized")

    # MinIO bucket + avatar policy (idempotent, blocking emas)
    init_storage()

    # Phase 7e — slow query listener (DB engine bilan birga)
    setup_slow_query_logging()

    # Phase 11b — chat WebSocket fan-out (Redis pub/sub)
    await ws_manager.attach_redis(redis_client)

    yield

    logger.info("app.stop")
    await ws_manager.shutdown()
    await redis_client.aclose()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.APP_DEBUG,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # Phase 7e — request ID + structured access logs (CORS'dan oldin)
    app.add_middleware(RequestIDMiddleware)

    # Phase 7f — Security headers + rate limit (innermost — har response'ga ta'sir)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_min=settings.RATE_LIMIT_REQUESTS_PER_MIN,
    )

    # CORS
    if settings.cors_origins_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-Request-ID"],
        )

    # Phase 7e — Prometheus /metrics
    setup_metrics(app)

    app.include_router(api_router)

    @app.get("/", tags=["root"])
    async def root() -> dict[str, str]:
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    return app


app = create_app()

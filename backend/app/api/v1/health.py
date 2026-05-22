from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    env: str
    timestamp: str


class ReadinessResponse(BaseModel):
    status: str
    checks: dict[str, str]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe — process ishlayotganini tekshiradi."""
    return HealthResponse(
        status="ok",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        env=settings.APP_ENV,
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
)
async def ready(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ReadinessResponse:
    """Readiness probe — tashqi bog'liqliklar (DB, Redis) tayyorligini tekshiradi."""
    checks: dict[str, str] = {}

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["database"] = f"error: {exc.__class__.__name__}"

    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["redis"] = f"error: {exc.__class__.__name__}"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return ReadinessResponse(status=overall, checks=checks)

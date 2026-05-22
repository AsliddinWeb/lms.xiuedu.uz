from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.db.base import Base  # noqa: F401 (re-export for backward compat)


def _create_engine() -> AsyncEngine:
    return create_async_engine(
        str(settings.DATABASE_URL),
        echo=settings.DATABASE_ECHO,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


engine: AsyncEngine = _create_engine()

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — bitta request uchun bitta session."""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

"""Pytest configuration — session-scoped event loop, ASGI client.

Asyncpg connection pool bitta event loop bilan bog'liq, shuning uchun
butun test session uchun bitta loop ishlatamiz (function-scoped emas).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings

# Phase 7f — testlarda umumiy rate limit o'chirilgan
settings.RATE_LIMIT_ENABLED = False

from app.main import app  # noqa: E402  — settings'dan keyin import qilinishi shart


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

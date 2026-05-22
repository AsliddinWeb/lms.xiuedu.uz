"""Async retry helper — Phase 7c.

HEMIS sync uchun exponential backoff bilan retry mexanizmi.
3 ta urinish: 0s → 1s → 3s (jami ~4s eng yomon holatda).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


async def retry_async(
    fn: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    backoff_seconds: tuple[float, ...] = (0.0, 1.0, 3.0),
    retry_on: tuple[type[Exception], ...] = (Exception,),
    label: str = "task",
) -> T:
    """`fn`'ni `attempts` marta urinib ko'radi.

    Har urinishda backoff_seconds[i] sekund kutadi (oldindan).
    Hammasi muvaffaqiyatsiz bo'lsa, oxirgi exception qayta ko'tariladi.
    """
    last_exc: Exception | None = None
    for i in range(attempts):
        delay = backoff_seconds[i] if i < len(backoff_seconds) else backoff_seconds[-1]
        if delay > 0:
            await asyncio.sleep(delay)
        try:
            return await fn()
        except retry_on as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning(
                "retry.attempt_failed",
                label=label,
                attempt=i + 1,
                of=attempts,
                error=str(exc),
            )
    assert last_exc is not None
    raise last_exc

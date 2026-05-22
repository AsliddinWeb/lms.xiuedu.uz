"""Brute-force himoyasi — Redis sliding window.

5 ta noto'g'ri urinish (IP yoki email bo'yicha) → 15 daqiqa lock.
Spec: docs/03-modules/01-auth.md, docs/07-devops/04-security.md
"""

from __future__ import annotations

from redis.asyncio import Redis

from app.modules.auth.exceptions import AccountLockedError

MAX_ATTEMPTS = 5
BLOCK_SECONDS = 15 * 60  # 15 daqiqa
WINDOW_SECONDS = 15 * 60  # 15 daqiqa rolling window

_PREFIX = "auth:fail"
_LOCK_PREFIX = "auth:lock"


def _attempt_key(scope: str, ident: str) -> str:
    return f"{_PREFIX}:{scope}:{ident}"


def _lock_key(scope: str, ident: str) -> str:
    return f"{_LOCK_PREFIX}:{scope}:{ident}"


async def assert_not_locked(redis: Redis, *, ip: str, email: str | None) -> None:
    """Login boshlanishidan oldin chaqiriladi. Bloklangan bo'lsa — 423."""
    for scope, ident in (("ip", ip), ("email", email)):
        if not ident:
            continue
        ttl = await redis.ttl(_lock_key(scope, ident))
        if ttl and ttl > 0:
            raise AccountLockedError(retry_after_seconds=ttl)


async def record_failed_attempt(redis: Redis, *, ip: str, email: str | None) -> None:
    """Failed login dan keyin chaqiriladi. MAX_ATTEMPTS ga yetganda lock."""
    for scope, ident in (("ip", ip), ("email", email)):
        if not ident:
            continue
        key = _attempt_key(scope, ident)
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, WINDOW_SECONDS)
        if count >= MAX_ATTEMPTS:
            await redis.set(_lock_key(scope, ident), "1", ex=BLOCK_SECONDS)
            await redis.delete(key)


async def reset_attempts(redis: Redis, *, ip: str, email: str | None) -> None:
    """Muvaffaqiyatli login'dan keyin counter'larni tozalash."""
    keys = [_attempt_key("ip", ip)]
    if email:
        keys.append(_attempt_key("email", email))
    if keys:
        await redis.delete(*keys)

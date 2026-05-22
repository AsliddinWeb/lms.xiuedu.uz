"""HEMIS JWT cache (Redis) — Phase 10c.

LMS user uchun HEMIS API tokenini saqlaymiz — har request'da qayta login qilmaslik
uchun. TTL `settings.HEMIS_TOKEN_CACHE_TTL` (default 600s = 10 min).

Token cache scope:
- Student token: keyed by user_id
- Tutor token:   keyed by user_id (alohida namespace)
- Backend token: env-dan kelgan static value (cache shart emas)

Foydalanish:
    cache = HemisTokenCache(redis)
    await cache.set_student(user_id=42, token="...", refresh="...")
    pair = await cache.get_student(user_id=42)
    # pair = {"token": str, "refresh_token": str | None} | None
"""

from __future__ import annotations

import json

from redis.asyncio import Redis

from app.core.config import settings


_STUDENT_PREFIX = "hemis:student-token:"
_TUTOR_PREFIX = "hemis:tutor-token:"


class HemisTokenCache:
    """Redis-backed cache for HEMIS JWT tokens."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis
        self.ttl = settings.HEMIS_TOKEN_CACHE_TTL

    async def set_student(
        self, user_id: int, token: str, refresh: str | None = None
    ) -> None:
        key = f"{_STUDENT_PREFIX}{user_id}"
        payload = json.dumps({"token": token, "refresh_token": refresh})
        await self.redis.set(key, payload, ex=self.ttl)

    async def get_student(self, user_id: int) -> dict[str, str | None] | None:
        key = f"{_STUDENT_PREFIX}{user_id}"
        raw = await self.redis.get(key)
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def clear_student(self, user_id: int) -> None:
        await self.redis.delete(f"{_STUDENT_PREFIX}{user_id}")

    async def set_tutor(
        self, user_id: int, token: str, refresh: str | None = None
    ) -> None:
        key = f"{_TUTOR_PREFIX}{user_id}"
        payload = json.dumps({"token": token, "refresh_token": refresh})
        await self.redis.set(key, payload, ex=self.ttl)

    async def get_tutor(self, user_id: int) -> dict[str, str | None] | None:
        key = f"{_TUTOR_PREFIX}{user_id}"
        raw = await self.redis.get(key)
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def clear_tutor(self, user_id: int) -> None:
        await self.redis.delete(f"{_TUTOR_PREFIX}{user_id}")

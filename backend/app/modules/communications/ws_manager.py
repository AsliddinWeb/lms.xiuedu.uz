"""WebSocket connection manager — Phase 11b.

Bir nechta worker bilan ishlashi uchun Redis pub/sub'dan foydalanadi:

    1. Mahalliy `_local` map — bir process ichidagi user->WebSocket bog'lanishlar
    2. Redis kanal `chat:user:{user_id}` — boshqa workerlardan kelgan eventlar
    3. Har bir worker startup'da Redis pub/sub listener boshlaydi va kanal nomi
       o'zining mahalliy map'idagi user bo'yicha mos kelsa, ulangan socketlarga
       jo'natadi.

`publish(user_id, payload)` — istalgan workerdan event chiqaradi va u kerakli
workerga (ya'ni user ulangan workerga) Redis pub/sub orqali yetib boradi.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from contextlib import suppress
from typing import Any

from fastapi import WebSocket
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_USER_CHANNEL_PREFIX = "chat:user:"
_CONV_CHANNEL_PREFIX = "chat:conv:"


class ConnectionManager:
    """User -> ulangan WebSocketlar (bir user bir nechta brauzer/tabdan)."""

    def __init__(self) -> None:
        self._local: dict[int, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()
        self._pubsub_task: asyncio.Task[None] | None = None
        self._redis: Redis | None = None
        self._subscribed_users: set[int] = set()
        self._pubsub = None  # type: ignore[assignment]

    # ------------------------------------------------------------------ setup
    async def attach_redis(self, redis: Redis) -> None:
        """App startup'da bir marta chaqiriladi."""
        self._redis = redis
        if self._pubsub is None:
            self._pubsub = redis.pubsub()
            self._pubsub_task = asyncio.create_task(self._pubsub_loop())

    async def shutdown(self) -> None:
        if self._pubsub_task is not None:
            self._pubsub_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._pubsub_task
            self._pubsub_task = None
        if self._pubsub is not None:
            with suppress(Exception):
                await self._pubsub.close()
            self._pubsub = None
        # Mahalliy socketlarni yopish — app shutdown'da
        async with self._lock:
            for sockets in list(self._local.values()):
                for ws in list(sockets):
                    with suppress(Exception):
                        await ws.close()
            self._local.clear()

    # ------------------------------------------------------------------ connect
    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._local[user_id].add(websocket)
            need_subscribe = user_id not in self._subscribed_users
            if need_subscribe:
                self._subscribed_users.add(user_id)
        if need_subscribe and self._pubsub is not None:
            channel = f"{_USER_CHANNEL_PREFIX}{user_id}"
            await self._pubsub.subscribe(channel)
            logger.debug("ws: subscribed to %s", channel)

    async def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            sockets = self._local.get(user_id)
            if sockets is not None:
                sockets.discard(websocket)
                if not sockets:
                    self._local.pop(user_id, None)
                    self._subscribed_users.discard(user_id)
                    should_unsubscribe = True
                else:
                    should_unsubscribe = False
            else:
                should_unsubscribe = False
        if should_unsubscribe and self._pubsub is not None:
            with suppress(Exception):
                await self._pubsub.unsubscribe(f"{_USER_CHANNEL_PREFIX}{user_id}")

    # ------------------------------------------------------------------ publish
    async def publish_to_users(
        self, user_ids: list[int], payload: dict[str, Any]
    ) -> None:
        """Eventni har bir user'ga (uning barcha workerlaridagi socketlariga) jo'natadi.

        Redis bo'lmasa local fallback ishlaydi (dev/test).
        """
        if not user_ids:
            return
        data = json.dumps(payload, default=str)
        if self._redis is not None:
            # Pipeline orqali bitta round-trip
            pipe = self._redis.pipeline()
            for uid in user_ids:
                pipe.publish(f"{_USER_CHANNEL_PREFIX}{uid}", data)
            await pipe.execute()
        else:
            # Local fallback
            await self._deliver_locally(user_ids, payload)

    # ------------------------------------------------------------------ internals
    async def _deliver_locally(
        self, user_ids: list[int], payload: dict[str, Any]
    ) -> None:
        text = json.dumps(payload, default=str)
        for uid in user_ids:
            sockets = list(self._local.get(uid, ()))
            for ws in sockets:
                try:
                    await ws.send_text(text)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("ws: send failed user=%s err=%s", uid, exc)
                    await self.disconnect(uid, ws)

    async def _pubsub_loop(self) -> None:
        assert self._pubsub is not None
        while True:
            try:
                msg = await self._pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if msg is None:
                    await asyncio.sleep(0)
                    continue
                channel = msg.get("channel")
                data = msg.get("data")
                if not channel or not data:
                    continue
                if not channel.startswith(_USER_CHANNEL_PREFIX):
                    continue
                try:
                    user_id = int(channel[len(_USER_CHANNEL_PREFIX):])
                except ValueError:
                    continue
                try:
                    payload = json.loads(data)
                except json.JSONDecodeError:
                    logger.warning("ws: invalid json on %s", channel)
                    continue
                await self._deliver_locally([user_id], payload)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.exception("ws: pubsub loop error: %s", exc)
                await asyncio.sleep(0.5)


# App-level singleton — main.py startup'da attach_redis chaqiradi
manager = ConnectionManager()

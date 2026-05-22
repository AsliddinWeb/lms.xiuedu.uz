"""Native WebRTC provider — LiveKit self-hosted (Phase 5).

Tashqi xizmat YO'Q. LiveKit docker konteynerimizda ishlaydi
(docker-compose.yml: `livekit` service, port 7880).

JWT token spec: https://docs.livekit.io/realtime/concepts/authentication/
Claim'lar:
  iss = LIVEKIT_API_KEY
  sub = participant identity (user id)
  name = participant display name
  nbf = unix epoch (now)
  exp = unix epoch (now + TTL)
  video = {
    room: "xiu-live-{session_id}",
    roomJoin: true,
    canPublish: bool (host=True, talaba=True ham — barchasi gapira oladi),
    canPublishData: true,
    canSubscribe: true,
  }
  metadata = JSON string ({ is_host, email, ... })
"""

from __future__ import annotations

import json
import time

from jose import jwt

from app.core.config import settings
from app.modules.live.providers.base import (
    LiveProvider,
    ProviderJoinInfo,
    ProviderUser,
)


class NativeProvider:
    """LiveKit asosida native WebRTC — hech qanday tashqi servis."""

    name = "native"

    def make_room_name(self, session_id: int) -> str:
        return f"xiu-live-{session_id}"

    def build_join_info(
        self, *, room_name: str, user: ProviderUser
    ) -> ProviderJoinInfo:
        token = self._issue_token(room=room_name, user=user)
        return ProviderJoinInfo(
            provider=self.name,
            room_name=room_name,
            # Brauzer LiveKit'ga ulanish uchun WS URL
            join_url=settings.LIVEKIT_URL_PUBLIC,
            embed_token=token,
            embed_config={
                "url": settings.LIVEKIT_URL_PUBLIC,
                "is_host": user.is_host,
            },
        )

    def _issue_token(self, *, room: str, user: ProviderUser) -> str:
        now = int(time.time())
        metadata = json.dumps(
            {
                "is_host": user.is_host,
                "email": user.email,
                "avatar_url": user.avatar_url or "",
            }
        )
        claims = {
            "iss": settings.LIVEKIT_API_KEY,
            "sub": str(user.id),
            "name": user.name,
            "nbf": now,
            "exp": now + settings.LIVEKIT_TOKEN_TTL_SECONDS,
            "video": {
                "room": room,
                "roomJoin": True,
                # Host kerak bo'lsa keyinroq cheklash mumkin
                # (canPublish=False qilib talabani faqat tinglovchi qilish)
                "canPublish": True,
                "canPublishData": True,
                "canSubscribe": True,
                "canUpdateOwnMetadata": True,
                # Host moderator huquqlari — boshqalarni mute qilish va h.k.
                "roomAdmin": user.is_host,
                "roomCreate": user.is_host,
            },
            "metadata": metadata,
        }
        return jwt.encode(claims, settings.LIVEKIT_API_SECRET, algorithm="HS256")


# Sanity check Protocol implementation
_provider: LiveProvider = NativeProvider()

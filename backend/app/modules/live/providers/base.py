"""Live provider Protocol va umumiy data class'lar."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProviderUser:
    """Provider'ga uzatiladigan minimal user info (JWT claim uchun)."""

    id: int
    name: str
    email: str
    is_host: bool
    avatar_url: str | None = None


@dataclass(frozen=True)
class ProviderJoinInfo:
    """Frontend'ga qaytariladigan provider-agnostic join payload.

    `embed_token` Jitsi/Zoom uchun asosiy auth tokeni; BBB'da bo'sh bo'lishi mumkin
    chunki BBB join-link to'g'ridan-to'g'ri ishlaydi.
    `embed_config` provider'ga xos qo'shimcha data (frontend SDK init uchun).
    """

    provider: str
    room_name: str
    join_url: str
    embed_token: str | None = None
    embed_config: dict | None = None


class LiveProvider(Protocol):
    """Har provider uchun yagona interface."""

    name: str

    def make_room_name(self, session_id: int) -> str:
        """Session id'ni provider-friendly room name'ga aylantirish."""

    def build_join_info(
        self, *, room_name: str, user: ProviderUser
    ) -> ProviderJoinInfo:
        """Foydalanuvchi uchun provider URL + token quradi."""

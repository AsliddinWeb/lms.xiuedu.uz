"""Live provider abstraction (Phase 5).

Native — yagona provider (LiveKit self-hosted, tashqi xizmatsiz).
"""

from __future__ import annotations

from app.modules.live.providers.base import (
    LiveProvider,
    ProviderJoinInfo,
    ProviderUser,
)
from app.modules.live.providers.native import NativeProvider

__all__ = [
    "LiveProvider",
    "NativeProvider",
    "ProviderJoinInfo",
    "ProviderUser",
    "get_provider",
]


def get_provider(name: str) -> LiveProvider:
    """Provider nomi → instance. Faqat 'native' qo'llab-quvvatlanadi."""
    if name == "native":
        return NativeProvider()
    raise ValueError(f"Provider qo'llab-quvvatlanmaydi: {name}")

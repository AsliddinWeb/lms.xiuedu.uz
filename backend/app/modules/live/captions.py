"""Live caption service — Phase 9c.

Real-time subtitle bo'laklarini saqlash + VTT formatga konvertatsiya.
Pedagog brauzeridagi Web Speech API yoki kelajakda Whisper'dan keladi.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.live.models import LiveCaption, LiveSession


async def _get_session(db: AsyncSession, session_id: int) -> LiveSession:
    s = (
        await db.execute(select(LiveSession).where(LiveSession.id == session_id))
    ).scalar_one_or_none()
    if s is None:
        raise NotFoundError("Live session topilmadi")
    return s


async def add_batch(
    db: AsyncSession,
    session_id: int,
    items: list[dict],
    *,
    speaker_user_id: int | None = None,
) -> int:
    """Bir nechta caption'ni bir vaqtda saqlash.

    items: [{start_ms, end_ms, text, lang}]
    """
    await _get_session(db, session_id)
    if not items:
        return 0
    rows = [
        LiveCaption(
            session_id=session_id,
            speaker_user_id=speaker_user_id,
            start_ms=int(i["start_ms"]),
            end_ms=int(i["end_ms"]),
            text=str(i["text"]),
            lang=str(i.get("lang") or "uz")[:10],
        )
        for i in items
        if i.get("text")
    ]
    db.add_all(rows)
    await db.flush()
    return len(rows)


async def list_for_session(
    db: AsyncSession, session_id: int
) -> list[LiveCaption]:
    stmt = (
        select(LiveCaption)
        .where(LiveCaption.session_id == session_id)
        .order_by(LiveCaption.start_ms.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


def _ms_to_vtt_timestamp(ms: int) -> str:
    """3600123 → '01:00:00.123'."""
    total_seconds = ms // 1000
    millis = ms % 1000
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}.{millis:03d}"


async def build_vtt(db: AsyncSession, session_id: int) -> str:
    """WebVTT formatda matn qaytaradi — `<video><track>` uchun."""
    items = await list_for_session(db, session_id)
    lines = ["WEBVTT", ""]
    for i, c in enumerate(items, 1):
        lines.append(str(i))
        lines.append(
            f"{_ms_to_vtt_timestamp(c.start_ms)} --> {_ms_to_vtt_timestamp(c.end_ms)}"
        )
        lines.append(c.text)
        lines.append("")
    return "\n".join(lines)

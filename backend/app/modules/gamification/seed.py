"""Dastlabki badge katalogi — Phase 11e.

Idempotent — `seed_badges(db)` chaqirilganda mavjudini o'tkazib yuboradi.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.gamification.models import Badge

DEFAULT_BADGES: list[dict] = [
    {
        "code": "first_lesson",
        "title": "Birinchi qadam",
        "description": "Birinchi darsni tugatdingiz",
        "category": "progress",
        "points_reward": 5,
    },
    {
        "code": "first_course",
        "title": "Bilim cho'qqisi",
        "description": "Birinchi kursni muvaffaqiyatli tugatdingiz",
        "category": "achievement",
        "points_reward": 50,
    },
    {
        "code": "course_master",
        "title": "Kurs ustasi",
        "description": "5 ta kursni tugatdingiz",
        "category": "mastery",
        "points_reward": 200,
    },
    {
        "code": "exam_ace",
        "title": "A'lochi",
        "description": "Imtihonda 100% natija ko'rsatdingiz",
        "category": "mastery",
        "points_reward": 100,
    },
    {
        "code": "social_butterfly",
        "title": "Faol muloqotchi",
        "description": "10 ta izoh qoldirdingiz",
        "category": "social",
        "points_reward": 30,
    },
    {
        "code": "helpful_voice",
        "title": "Foydali ovoz",
        "description": "Forum javoblaringizga 10 marta like olindi",
        "category": "social",
        "points_reward": 50,
    },
]


async def seed_badges(db: AsyncSession) -> int:
    """Yangi badge'larni qo'shadi, mavjudini tegmasdan o'tib yuboradi."""
    existing_codes = set(
        (await db.execute(select(Badge.code))).scalars().all()
    )
    added = 0
    now = datetime.now(UTC)
    for row in DEFAULT_BADGES:
        if row["code"] in existing_codes:
            continue
        db.add(
            Badge(
                code=row["code"],
                title=row["title"],
                description=row["description"],
                category=row["category"],
                points_reward=row["points_reward"],
                is_hidden=False,
                is_active=True,
                created_at=now,
            )
        )
        added += 1
    if added:
        await db.flush()
    return added

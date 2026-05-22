"""iCalendar (.ics) generator for live sessions.

Token-based shaxsiy URL: foydalanuvchi `?token=...` bilan ochib o'zining
yaqinlashayotgan live darslarini Google/Outlook kalendarga sync qila oladi.

Token: HMAC-SHA256(user_id, JWT_SECRET_KEY) — auth header'dan farqli o'laroq
URL ichida bo'lishi mumkin (kalendar app'lari Authorization header
yubora olmaydi).
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime
from typing import Sequence

from app.core.config import settings


def make_calendar_token(user_id: int) -> str:
    """HMAC-SHA256(user_id|tenant_code, JWT_SECRET_KEY) — uzun-yashar token."""
    msg = f"ical:{user_id}:{settings.TENANT_CODE}".encode()
    return hmac.new(
        settings.JWT_SECRET_KEY.encode(), msg, hashlib.sha256
    ).hexdigest()


def verify_calendar_token(user_id: int, token: str) -> bool:
    expected = make_calendar_token(user_id)
    return hmac.compare_digest(expected, token)


def _ics_escape(text: str) -> str:
    """RFC 5545 text escaping."""
    return (
        text.replace("\\", "\\\\")
        .replace(",", "\\,")
        .replace(";", "\\;")
        .replace("\n", "\\n")
    )


def _ics_dt(dt: datetime) -> str:
    """UTC vaqtni RFC 5545 formatida (YYYYMMDDTHHMMSSZ)."""
    return dt.strftime("%Y%m%dT%H%M%SZ")


def build_ics(
    sessions: Sequence[object], *, calendar_name: str = "XIU LMS Live"
) -> str:
    """LiveSession ro'yxatidan iCalendar matnini quradi.

    sessions — LiveSession SQLAlchemy obyekt iterable'i. Faqat
    quyidagi maydonlar o'qiladi:
        id, title, description, scheduled_start, scheduled_end,
        provider_meeting_id, status
    """
    now = _ics_dt(datetime.utcnow())
    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//XIU LMS//Live//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_ics_escape(calendar_name)}",
    ]
    for s in sessions:
        if getattr(s, "status", "") == "cancelled":
            continue
        uid = f"live-{s.id}@xiuedu.uz"
        title = _ics_escape(getattr(s, "title", "") or "Live class")
        desc_raw = getattr(s, "description", None) or ""
        description = _ics_escape(desc_raw)
        location = (
            f"XIU LMS ({getattr(s, 'provider_meeting_id', '') or 'online'})"
        )
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now}",
                f"DTSTART:{_ics_dt(s.scheduled_start)}",
                f"DTEND:{_ics_dt(s.scheduled_end)}",
                f"SUMMARY:{title}",
                f"DESCRIPTION:{description}",
                f"LOCATION:{_ics_escape(location)}",
                f"STATUS:{'CONFIRMED' if s.status != 'cancelled' else 'CANCELLED'}",
                "BEGIN:VALARM",
                "ACTION:DISPLAY",
                f"DESCRIPTION:{title}",
                "TRIGGER:-PT15M",
                "END:VALARM",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    # RFC 5545 CRLF line endings
    return "\r\n".join(lines) + "\r\n"

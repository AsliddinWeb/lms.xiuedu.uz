"""Smart anomaly scoring — Phase 9f.

Existing proctoring eventlar + snapshot signal'larini birlashtirib, qoidabuzarlik
patternlarini aniqlaydi. Oddiy `violation_score` (event weights yig'indisi)
ustiga **AI-style heuristic layer** quradi:

    Detektorlar:
      - combo_paste_tab    : tab_switch + paste_attempt 10s ichida
      - burst              : 60s da ≥5 ta event
      - low_face_avg       : snapshot face_match_score o'rtacha <0.5
      - frequent_gaze_off  : ≥3 ta gaze_off event
      - identity_mismatch  : multiple_faces critical event
      - devtools           : devtools_opened event

Har detektorda fired bo'lsa, smart_score'ga ma'lum og'irlik qo'shiladi.
Maksimal 100. Result: smart_score (0..100) + flags list.

`recommended_action`:
    score < 30       → "approve"
    30 <= score < 60 → "review"
    score >= 60      → "invalidate" (lekin auto emas — pedagog qarori)
"""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.exams.models import ExamAttempt, ProctoringEvent, ProctoringSnapshot


# Detektor og'irliklari (jami max ~140, lekin score 100'da cap qilamiz)
DETECTOR_WEIGHTS = {
    "combo_paste_tab": 25,
    "burst": 20,
    "low_face_avg": 30,
    "frequent_gaze_off": 15,
    "identity_mismatch": 40,
    "devtools": 25,
}


class SmartFlag(TypedDict):
    type: str
    weight: int
    detail: str


class SmartScoreResult(TypedDict):
    score: int
    flags: list[SmartFlag]
    recommended_action: str


def _detect_combo_paste_tab(events: list[ProctoringEvent]) -> SmartFlag | None:
    """Tab switch + paste 10s ichida — tashqi manbadan ko'chirish belgisi."""
    tab_times = [e.occurred_at for e in events if e.event_type in ("tab_switch", "visibility_lost")]
    paste_times = [e.occurred_at for e in events if e.event_type == "paste_attempt"]
    if not tab_times or not paste_times:
        return None
    threshold = timedelta(seconds=10)
    combos = 0
    for tt in tab_times:
        for pt in paste_times:
            if abs((pt - tt).total_seconds()) <= threshold.total_seconds():
                combos += 1
                break
    if combos == 0:
        return None
    return {
        "type": "combo_paste_tab",
        "weight": DETECTOR_WEIGHTS["combo_paste_tab"],
        "detail": f"{combos} ta tab_switch+paste kombinatsiyasi (10s ichida)",
    }


def _detect_burst(events: list[ProctoringEvent]) -> SmartFlag | None:
    """60s deraza ichida ≥5 ta event — panik holat / aktiv qoidabuzarlik."""
    if len(events) < 5:
        return None
    sorted_events = sorted(events, key=lambda e: e.occurred_at)
    window = timedelta(seconds=60)
    for i, e in enumerate(sorted_events):
        count_in_window = sum(
            1 for j in range(i, len(sorted_events))
            if sorted_events[j].occurred_at - e.occurred_at <= window
        )
        if count_in_window >= 5:
            return {
                "type": "burst",
                "weight": DETECTOR_WEIGHTS["burst"],
                "detail": f"60s ichida {count_in_window} ta event (peak)",
            }
    return None


def _detect_low_face_avg(snapshots: list[ProctoringSnapshot]) -> SmartFlag | None:
    """Reference rasm bilan o'rtacha match score < 0.5 — boshqa odam bo'lishi mumkin."""
    scores = [
        float(s.face_match_score)
        for s in snapshots
        if s.face_match_score is not None and s.face_count == 1
    ]
    if len(scores) < 3:
        return None
    avg = sum(scores) / len(scores)
    if avg >= 0.5:
        return None
    return {
        "type": "low_face_avg",
        "weight": DETECTOR_WEIGHTS["low_face_avg"],
        "detail": f"O'rtacha face match {avg * 100:.0f}% ({len(scores)} snapshot)",
    }


def _detect_frequent_gaze_off(events: list[ProctoringEvent]) -> SmartFlag | None:
    n = sum(1 for e in events if e.event_type == "gaze_off")
    if n < 3:
        return None
    return {
        "type": "frequent_gaze_off",
        "weight": DETECTOR_WEIGHTS["frequent_gaze_off"],
        "detail": f"{n} marta ekrandan qaragan",
    }


def _detect_identity_mismatch(events: list[ProctoringEvent]) -> SmartFlag | None:
    n = sum(1 for e in events if e.event_type == "multiple_faces")
    if n == 0:
        return None
    return {
        "type": "identity_mismatch",
        "weight": DETECTOR_WEIGHTS["identity_mismatch"],
        "detail": f"{n} ta multiple_faces / yuz mismatch",
    }


def _detect_devtools(events: list[ProctoringEvent]) -> SmartFlag | None:
    n = sum(1 for e in events if e.event_type == "devtools_opened")
    if n == 0:
        return None
    return {
        "type": "devtools",
        "weight": DETECTOR_WEIGHTS["devtools"],
        "detail": f"DevTools {n} marta ochilgan",
    }


def _recommended(score: int) -> str:
    if score >= 60:
        return "invalidate"
    if score >= 30:
        return "review"
    return "approve"


async def compute_smart_score(
    db: AsyncSession, attempt_id: int
) -> SmartScoreResult:
    """Attempt uchun smart anomaly score hisoblaydi.

    Tegishli ma'lumotlar (events + snapshots) DB'dan o'qiladi, har detector
    chaqiriladi, og'irliklar yig'iladi.
    """
    events = list(
        (
            await db.execute(
                select(ProctoringEvent).where(ProctoringEvent.attempt_id == attempt_id)
            )
        ).scalars().all()
    )
    snapshots = list(
        (
            await db.execute(
                select(ProctoringSnapshot).where(
                    ProctoringSnapshot.attempt_id == attempt_id
                )
            )
        ).scalars().all()
    )

    flags: list[SmartFlag] = []
    for detector in (
        _detect_combo_paste_tab,
        _detect_burst,
        _detect_frequent_gaze_off,
        _detect_identity_mismatch,
        _detect_devtools,
    ):
        flag = detector(events)
        if flag is not None:
            flags.append(flag)

    snap_flag = _detect_low_face_avg(snapshots)
    if snap_flag is not None:
        flags.append(snap_flag)

    score = min(100, sum(f["weight"] for f in flags))

    return {
        "score": score,
        "flags": flags,
        "recommended_action": _recommended(score),
    }


async def apply_smart_score(db: AsyncSession, attempt_id: int) -> SmartScoreResult:
    """Compute + persist on ExamAttempt."""
    result = await compute_smart_score(db, attempt_id)
    attempt = (
        await db.execute(select(ExamAttempt).where(ExamAttempt.id == attempt_id))
    ).scalar_one_or_none()
    if attempt is not None:
        attempt.smart_score = result["score"]
        attempt.smart_flags = [dict(f) for f in result["flags"]]
        await db.flush()
    return result

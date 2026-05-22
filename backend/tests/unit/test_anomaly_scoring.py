"""Phase 9f — Smart anomaly scoring detektorlari uchun unit testlar.

DB chaqirmaslik uchun har bir detector private funksiya alohida testlanadi
soxta event/snapshot obyektlari bilan.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.modules.exams.anomaly import (
    DETECTOR_WEIGHTS,
    _detect_burst,
    _detect_combo_paste_tab,
    _detect_devtools,
    _detect_frequent_gaze_off,
    _detect_identity_mismatch,
    _detect_low_face_avg,
    _recommended,
)


@dataclass
class FakeEvent:
    event_type: str
    occurred_at: datetime


@dataclass
class FakeSnap:
    face_count: int | None
    face_match_score: float | None


def _now() -> datetime:
    return datetime(2026, 5, 19, 12, 0, 0, tzinfo=timezone.utc)


# ---- recommended_action thresholds ----

def test_recommended_low():
    assert _recommended(0) == "approve"
    assert _recommended(29) == "approve"


def test_recommended_mid():
    assert _recommended(30) == "review"
    assert _recommended(59) == "review"


def test_recommended_high():
    assert _recommended(60) == "invalidate"
    assert _recommended(100) == "invalidate"


# ---- combo_paste_tab ----

def test_combo_paste_tab_fires_when_close():
    t0 = _now()
    events = [
        FakeEvent("tab_switch", t0),
        FakeEvent("paste_attempt", t0 + timedelta(seconds=5)),
    ]
    flag = _detect_combo_paste_tab(events)
    assert flag is not None
    assert flag["type"] == "combo_paste_tab"
    assert flag["weight"] == DETECTOR_WEIGHTS["combo_paste_tab"]


def test_combo_paste_tab_silent_when_far():
    t0 = _now()
    events = [
        FakeEvent("tab_switch", t0),
        FakeEvent("paste_attempt", t0 + timedelta(seconds=60)),
    ]
    assert _detect_combo_paste_tab(events) is None


def test_combo_paste_tab_silent_without_paste():
    t0 = _now()
    events = [FakeEvent("tab_switch", t0)]
    assert _detect_combo_paste_tab(events) is None


# ---- burst ----

def test_burst_fires_with_five_events_in_window():
    t0 = _now()
    events = [FakeEvent("tab_switch", t0 + timedelta(seconds=i * 5)) for i in range(5)]
    flag = _detect_burst(events)
    assert flag is not None
    assert flag["weight"] == DETECTOR_WEIGHTS["burst"]


def test_burst_silent_when_spread():
    t0 = _now()
    events = [FakeEvent("tab_switch", t0 + timedelta(seconds=i * 120)) for i in range(5)]
    assert _detect_burst(events) is None


def test_burst_silent_with_few_events():
    t0 = _now()
    events = [FakeEvent("tab_switch", t0 + timedelta(seconds=i)) for i in range(3)]
    assert _detect_burst(events) is None


# ---- low_face_avg ----

def test_low_face_avg_fires():
    snaps = [FakeSnap(face_count=1, face_match_score=0.3) for _ in range(5)]
    flag = _detect_low_face_avg(snaps)
    assert flag is not None
    assert flag["weight"] == DETECTOR_WEIGHTS["low_face_avg"]


def test_low_face_avg_silent_when_high():
    snaps = [FakeSnap(face_count=1, face_match_score=0.8) for _ in range(5)]
    assert _detect_low_face_avg(snaps) is None


def test_low_face_avg_silent_when_few_snapshots():
    snaps = [FakeSnap(face_count=1, face_match_score=0.2) for _ in range(2)]
    assert _detect_low_face_avg(snaps) is None


def test_low_face_avg_ignores_multi_face_and_null():
    snaps = [
        FakeSnap(face_count=2, face_match_score=0.1),  # multi face — ignore
        FakeSnap(face_count=1, face_match_score=None),  # null score — ignore
        FakeSnap(face_count=1, face_match_score=0.9),
    ]
    # Faqat 1 ta valid snap qoldi (< 3) — silent
    assert _detect_low_face_avg(snaps) is None


# ---- frequent_gaze_off ----

def test_frequent_gaze_off_fires_at_three():
    t0 = _now()
    events = [FakeEvent("gaze_off", t0 + timedelta(seconds=i * 10)) for i in range(3)]
    flag = _detect_frequent_gaze_off(events)
    assert flag is not None
    assert flag["weight"] == DETECTOR_WEIGHTS["frequent_gaze_off"]


def test_frequent_gaze_off_silent_at_two():
    t0 = _now()
    events = [FakeEvent("gaze_off", t0 + timedelta(seconds=i * 10)) for i in range(2)]
    assert _detect_frequent_gaze_off(events) is None


# ---- identity_mismatch ----

def test_identity_mismatch_fires():
    t0 = _now()
    events = [FakeEvent("multiple_faces", t0)]
    flag = _detect_identity_mismatch(events)
    assert flag is not None
    assert flag["weight"] == DETECTOR_WEIGHTS["identity_mismatch"]


def test_identity_mismatch_silent():
    t0 = _now()
    events = [FakeEvent("tab_switch", t0)]
    assert _detect_identity_mismatch(events) is None


# ---- devtools ----

def test_devtools_fires():
    t0 = _now()
    events = [FakeEvent("devtools_opened", t0)]
    flag = _detect_devtools(events)
    assert flag is not None
    assert flag["weight"] == DETECTOR_WEIGHTS["devtools"]


def test_devtools_silent():
    t0 = _now()
    events = [FakeEvent("paste_attempt", t0)]
    assert _detect_devtools(events) is None


# ---- DETECTOR_WEIGHTS sanity ----

def test_detector_weights_non_negative():
    for w in DETECTOR_WEIGHTS.values():
        assert w >= 0


def test_detector_weights_cover_expected_types():
    expected = {
        "combo_paste_tab",
        "burst",
        "low_face_avg",
        "frequent_gaze_off",
        "identity_mismatch",
        "devtools",
    }
    assert set(DETECTOR_WEIGHTS.keys()) == expected

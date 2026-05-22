"""Phase 6f — Violation weights va FLAG_THRESHOLD smoke testlari.

`compute_violation_score` async va DB chaqiradi, shuning uchun bu yerda
faqat constants va weight mapping consistency testlari.
"""

from __future__ import annotations

from app.modules.exams.proctoring import (
    FLAG_THRESHOLD,
    VALID_EVENT_TYPES,
    VIOLATION_WEIGHTS,
)


def test_flag_threshold_in_range():
    assert 0 < FLAG_THRESHOLD <= 100


def test_critical_events_alone_can_flag():
    # multiple_faces (50) × 2 ≥ FLAG_THRESHOLD ekanini tekshirish
    assert VIOLATION_WEIGHTS["multiple_faces"] * 2 >= FLAG_THRESHOLD


def test_devtools_high_severity():
    assert VIOLATION_WEIGHTS["devtools_opened"] >= 25


def test_paste_higher_than_copy():
    # Copy ko'pincha ruxsat etilgan; paste qattiqroq jazolanadi
    assert VIOLATION_WEIGHTS["paste_attempt"] > VIOLATION_WEIGHTS["copy_attempt"]


def test_no_negative_weights():
    for w in VIOLATION_WEIGHTS.values():
        assert w >= 0


def test_valid_event_types_consistent():
    assert VALID_EVENT_TYPES == set(VIOLATION_WEIGHTS.keys())


def test_visibility_returned_zero_weight():
    # Qaytishi qoidabuzarlik emas
    assert VIOLATION_WEIGHTS["visibility_returned"] == 0
    assert VIOLATION_WEIGHTS["fullscreen_entered"] == 0
    assert VIOLATION_WEIGHTS["face_found"] == 0


def test_known_event_keys():
    # Plan'da aytilgan asosiy event turlari mavjudligini tasdiqlash
    required = {
        "tab_switch",
        "fullscreen_exit",
        "face_lost",
        "multiple_faces",
        "paste_attempt",
        "devtools_opened",
    }
    assert required.issubset(VALID_EVENT_TYPES)

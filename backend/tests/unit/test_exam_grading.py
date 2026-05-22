"""Phase 6b — Auto-grading engine unit testlari.

Sof logika testlari (DB chaqirilmaydi). Question/Answer/QuestionOption
obyektlari in-memory tuziladi va grade_answer chaqiriladi.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.modules.exams.grading import grade_answer


def _q(**kwargs):
    """Question stub — faqat kerakli maydonlar."""
    defaults = dict(
        id=1,
        type="single_choice",
        title="?",
        points=Decimal("2.00"),
        options=[],
        correct_text=None,
        alternative_answers=None,
        exact_match=True,
        case_sensitive=False,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _opt(id: int, is_correct: bool):
    return SimpleNamespace(id=id, is_correct=is_correct)


def _ans(**kwargs):
    defaults = dict(
        selected_option_ids=None,
        text_answer=None,
        code_answer=None,
        file_url=None,
        auto_correct=None,
        points_earned=Decimal("0"),
        points_max=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# --- single_choice ---


def test_single_choice_correct():
    q = _q(type="single_choice", options=[_opt(10, True), _opt(11, False)])
    a = _ans(selected_option_ids=[10])
    grade_answer(a, q)
    assert a.auto_correct is True
    assert a.points_earned == Decimal("2.00")
    assert a.points_max == Decimal("2.00")


def test_single_choice_wrong():
    q = _q(type="single_choice", options=[_opt(10, True), _opt(11, False)])
    a = _ans(selected_option_ids=[11])
    grade_answer(a, q)
    assert a.auto_correct is False
    assert a.points_earned == Decimal("0")


def test_single_choice_no_selection():
    q = _q(type="single_choice", options=[_opt(10, True), _opt(11, False)])
    a = _ans(selected_option_ids=[])
    grade_answer(a, q)
    assert a.auto_correct is False
    assert a.points_earned == Decimal("0")


def test_single_choice_multiple_selected_rejected():
    # single_choice'da bir nechta tanlash xato deb qaraladi
    q = _q(type="single_choice", options=[_opt(10, True), _opt(11, False)])
    a = _ans(selected_option_ids=[10, 11])
    grade_answer(a, q)
    assert a.auto_correct is False
    assert a.points_earned == Decimal("0")


# --- true_false (single_choice bilan bir xil logika) ---


def test_true_false_correct():
    q = _q(type="true_false", points=Decimal("1.00"), options=[_opt(20, True), _opt(21, False)])
    a = _ans(selected_option_ids=[20])
    grade_answer(a, q)
    assert a.auto_correct is True
    assert a.points_earned == Decimal("1.00")


# --- multiple_choice ---


def test_multiple_choice_all_correct():
    q = _q(
        type="multiple_choice",
        points=Decimal("4.00"),
        options=[_opt(30, True), _opt(31, True), _opt(32, False)],
    )
    a = _ans(selected_option_ids=[30, 31])
    grade_answer(a, q)
    assert a.auto_correct is True
    assert a.points_earned == Decimal("4.00")


def test_multiple_choice_partial():
    q = _q(
        type="multiple_choice",
        points=Decimal("4.00"),
        options=[_opt(30, True), _opt(31, True), _opt(32, False)],
    )
    a = _ans(selected_option_ids=[30])
    grade_answer(a, q)
    assert a.auto_correct is False
    assert a.points_earned == Decimal("2.00")  # 1/2 of 4


def test_multiple_choice_wrong_selected_penalty():
    # noto'g'ri variant tanlangan bo'lsa → 0 (penalty)
    q = _q(
        type="multiple_choice",
        points=Decimal("4.00"),
        options=[_opt(30, True), _opt(31, True), _opt(32, False)],
    )
    a = _ans(selected_option_ids=[30, 31, 32])
    grade_answer(a, q)
    assert a.auto_correct is False
    assert a.points_earned == Decimal("0")


def test_multiple_choice_only_wrong_zero():
    q = _q(
        type="multiple_choice",
        points=Decimal("3.00"),
        options=[_opt(30, True), _opt(31, False)],
    )
    a = _ans(selected_option_ids=[31])
    grade_answer(a, q)
    assert a.auto_correct is False
    assert a.points_earned == Decimal("0")


def test_multiple_choice_empty_zero():
    q = _q(
        type="multiple_choice",
        points=Decimal("3.00"),
        options=[_opt(30, True), _opt(31, True)],
    )
    a = _ans(selected_option_ids=None)
    grade_answer(a, q)
    assert a.auto_correct is False
    assert a.points_earned == Decimal("0")


# --- short_text exact match ---


def test_short_text_exact_match_correct():
    q = _q(
        type="short_text",
        points=Decimal("2.00"),
        correct_text="Toshkent",
        exact_match=True,
        case_sensitive=False,
    )
    a = _ans(text_answer="toshkent")
    grade_answer(a, q)
    assert a.auto_correct is True
    assert a.points_earned == Decimal("2.00")


def test_short_text_case_sensitive():
    q = _q(
        type="short_text",
        points=Decimal("2.00"),
        correct_text="Python",
        exact_match=True,
        case_sensitive=True,
    )
    a = _ans(text_answer="python")
    grade_answer(a, q)
    assert a.auto_correct is False
    assert a.points_earned == Decimal("0")


def test_short_text_alternative_answers():
    q = _q(
        type="short_text",
        points=Decimal("2.00"),
        correct_text="Toshkent",
        alternative_answers=["Tashkent", "Tashkand"],
        exact_match=True,
        case_sensitive=False,
    )
    a = _ans(text_answer="tashkent")
    grade_answer(a, q)
    assert a.auto_correct is True
    assert a.points_earned == Decimal("2.00")


def test_short_text_empty_wrong():
    q = _q(
        type="short_text", points=Decimal("2.00"), correct_text="Toshkent", exact_match=True
    )
    a = _ans(text_answer="")
    grade_answer(a, q)
    assert a.auto_correct is False
    assert a.points_earned == Decimal("0")


def test_short_text_whitespace_trimmed():
    q = _q(
        type="short_text",
        points=Decimal("2.00"),
        correct_text="Toshkent",
        exact_match=True,
        case_sensitive=False,
    )
    a = _ans(text_answer="  Toshkent  ")
    grade_answer(a, q)
    assert a.auto_correct is True


def test_short_text_regex_mode():
    # exact_match=False → regex mode
    q = _q(
        type="short_text",
        points=Decimal("2.00"),
        correct_text=r"\d{4}",
        exact_match=False,
        case_sensitive=True,
    )
    a = _ans(text_answer="2026")
    grade_answer(a, q)
    assert a.auto_correct is True


def test_short_text_regex_invalid_falls_back_to_exact():
    # noto'g'ri regex sintaksis → exact compare bilan fallback
    q = _q(
        type="short_text",
        points=Decimal("1.00"),
        correct_text="[invalid(",
        exact_match=False,
        case_sensitive=False,
    )
    a = _ans(text_answer="[invalid(")
    grade_answer(a, q)
    assert a.auto_correct is True


# --- manual grading types ---


def test_essay_manual_grading():
    q = _q(type="essay", points=Decimal("10.00"))
    a = _ans(text_answer="Long answer...")
    grade_answer(a, q)
    assert a.auto_correct is None
    assert a.points_earned == Decimal("0")  # default; manual grading kelajakda yangilaydi
    assert a.points_max == Decimal("10.00")


def test_code_manual_grading():
    q = _q(type="code", points=Decimal("5.00"))
    a = _ans(code_answer="print('hi')")
    grade_answer(a, q)
    assert a.auto_correct is None
    assert a.points_max == Decimal("5.00")


def test_file_upload_manual_grading():
    q = _q(type="file_upload", points=Decimal("3.00"))
    a = _ans(file_url="https://s3/test.pdf")
    grade_answer(a, q)
    assert a.auto_correct is None
    assert a.points_max == Decimal("3.00")

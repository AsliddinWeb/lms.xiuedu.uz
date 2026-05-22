"""Auto-grading engine — Phase 6b.

Har savol turi uchun avtomatik baholash logikasi.

Qoidalar:
    - single_choice  : tanlangan option correct == True bo'lsa → full points
    - multiple_choice: barcha correct optionlar tanlangan + noto'g'ri yo'q → full
                       qisman: (correct_selected / total_correct) * points
                       agar noto'g'ri tanlangan bo'lsa → 0 ball (penalty)
    - true_false     : single_choice bilan bir xil
    - short_text     : exact_match yoki regex (alternative_answers + correct_text)
    - essay          : manual grading (auto_correct = None)
    - code           : manual grading (Phase 9'da kod runner)
    - file_upload    : manual grading

Funksiyalar javob *Answer* obyektini in-place yangilaydi:
    - auto_correct (bool | None)
    - points_earned (Decimal)
    - points_max (Decimal)
"""

from __future__ import annotations

import re
from decimal import Decimal

from app.modules.exams.models import Answer, Question, QuestionOption


def _grade_single_choice(
    answer: Answer, question: Question, options: list[QuestionOption]
) -> None:
    correct_id = next((o.id for o in options if o.is_correct), None)
    selected = answer.selected_option_ids or []
    if correct_id is not None and len(selected) == 1 and selected[0] == correct_id:
        answer.auto_correct = True
        answer.points_earned = question.points
    else:
        answer.auto_correct = False
        answer.points_earned = Decimal("0")


def _grade_multiple_choice(
    answer: Answer, question: Question, options: list[QuestionOption]
) -> None:
    correct_ids = {o.id for o in options if o.is_correct}
    selected_ids = set(answer.selected_option_ids or [])

    if not correct_ids:
        answer.auto_correct = False
        answer.points_earned = Decimal("0")
        return

    wrong_selected = selected_ids - correct_ids
    correct_selected = selected_ids & correct_ids

    if wrong_selected:
        # Penalty: noto'g'ri variant tanlangan
        answer.auto_correct = False
        answer.points_earned = Decimal("0")
        return

    if correct_selected == correct_ids:
        answer.auto_correct = True
        answer.points_earned = question.points
    else:
        # Qisman: faqat to'g'rilarning bir qismi tanlangan
        partial = Decimal(len(correct_selected)) / Decimal(len(correct_ids))
        answer.auto_correct = False
        answer.points_earned = (question.points * partial).quantize(Decimal("0.01"))


def _grade_short_text(answer: Answer, question: Question) -> None:
    raw = (answer.text_answer or "").strip()
    if not raw:
        answer.auto_correct = False
        answer.points_earned = Decimal("0")
        return

    candidates = [question.correct_text or ""]
    if question.alternative_answers:
        candidates.extend(question.alternative_answers)

    def _norm(s: str) -> str:
        s = s.strip()
        return s if question.case_sensitive else s.lower()

    raw_n = _norm(raw)
    matched = False
    for cand in candidates:
        cand_n = _norm(cand)
        if not cand_n:
            continue
        if question.exact_match:
            if raw_n == cand_n:
                matched = True
                break
        else:
            # Regex pattern sifatida ishlatish
            try:
                flags = 0 if question.case_sensitive else re.IGNORECASE
                if re.fullmatch(cand, raw, flags=flags):
                    matched = True
                    break
            except re.error:
                # Noto'g'ri regex bo'lsa, fallback exact compare
                if raw_n == cand_n:
                    matched = True
                    break

    answer.auto_correct = matched
    answer.points_earned = question.points if matched else Decimal("0")


def grade_answer(answer: Answer, question: Question) -> None:
    """Bitta javobni baholaydi — answer obyektini in-place yangilaydi.

    `question.options` selectinload qilingan bo'lishi shart (single/multi/tf uchun).
    Manual grading kerak bo'lsa, `auto_correct = None` qoldiriladi.
    """
    answer.points_max = question.points

    qtype = question.type
    if qtype == "single_choice" or qtype == "true_false":
        _grade_single_choice(answer, question, list(question.options))
    elif qtype == "multiple_choice":
        _grade_multiple_choice(answer, question, list(question.options))
    elif qtype == "short_text":
        _grade_short_text(answer, question)
    else:
        # essay, code, file_upload — manual grading kerak
        answer.auto_correct = None
        # points_earned ga tegmaymiz (0 default)


def grade_attempt_answers(answers: list[Answer], questions: list[Question]) -> None:
    """Bir urinishdagi barcha javoblarni baholaydi.

    Javob bo'lmagan savollar uchun ham 0 ball Answer yozish kerakmas —
    bu service.submit_attempt funksiyasining mas'uliyati.
    """
    by_qid = {q.id: q for q in questions}
    for ans in answers:
        q = by_qid.get(ans.question_id)
        if q is None:
            continue
        grade_answer(ans, q)

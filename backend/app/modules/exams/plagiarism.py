"""Exam answer plagiarism service — Phase 9e.

Har essay/short_text/code javob uchun boshqa attempt'lardagi xuddi shu savol
javoblari bilan TF-IDF cosine similarity hisoblanadi. Eng yaqin match'ning
ID'si va foiz score saqlanadi.

Threshold:
    < 30%  — toza
    30-60% — diqqat (sariq)
    60-80% — yuqori (qizil, manual review tavsiya)
    > 80%  — kritik (auto-flag)
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.text_similarity import best_match
from app.modules.exams.models import Answer, Question


PLAGIARISM_QUESTION_TYPES = ("essay", "short_text", "code")
MIN_TEXT_LENGTH = 30  # qisqaroq matn — false positive eng katta


def _extract_text(answer: Answer, qtype: str) -> str | None:
    """Javobdan plagiat tekshiruvi uchun matn olish."""
    if qtype == "code":
        return answer.code_answer
    if qtype in ("essay", "short_text"):
        return answer.text_answer
    return None


async def check_answer_against_others(
    db: AsyncSession, answer: Answer, question: Question
) -> tuple[Decimal | None, int | None]:
    """Berilgan javobni xuddi shu savol bo'yicha boshqa attempt'lar javoblari
    bilan solishtirish. Returns (score_pct, match_answer_id) yoki (None, None).
    """
    if question.type not in PLAGIARISM_QUESTION_TYPES:
        return None, None
    text = _extract_text(answer, question.type)
    if not text or len(text.strip()) < MIN_TEXT_LENGTH:
        return None, None

    # Bu attempt'ning bo'lmaganini olish (boshqa talabalar)
    stmt = (
        select(Answer)
        .where(
            Answer.question_id == question.id,
            Answer.id != answer.id,
        )
    )
    rows = (await db.execute(stmt)).scalars().all()
    corpus: list[tuple[int, str]] = []
    for other in rows:
        other_text = _extract_text(other, question.type)
        if other_text and len(other_text.strip()) >= MIN_TEXT_LENGTH:
            corpus.append((other.id, other_text))

    if not corpus:
        return Decimal("0"), None

    match_id, score = best_match(text, corpus)
    score_pct = Decimal(str(round(score * 100, 2)))
    return score_pct, match_id


async def check_attempt_plagiarism(db: AsyncSession, attempt_id: int) -> int:
    """Attempt'dagi barcha plagiat-tekshiruvga loyiq javoblarni tekshiradi.

    Returns: tekshirilgan javoblar soni.
    """
    from sqlalchemy.orm import selectinload
    from app.modules.exams.models import ExamAttempt

    stmt = (
        select(ExamAttempt)
        .where(ExamAttempt.id == attempt_id)
        .options(selectinload(ExamAttempt.answers).selectinload(Answer.question))
    )
    attempt = (await db.execute(stmt)).scalar_one_or_none()
    if attempt is None:
        return 0

    now = datetime.now(UTC)
    checked = 0
    for ans in attempt.answers:
        q = ans.question
        if q is None or q.type not in PLAGIARISM_QUESTION_TYPES:
            continue
        try:
            score, match_id = await check_answer_against_others(db, ans, q)
            if score is not None:
                ans.plagiarism_score = score
                ans.plagiarism_match_answer_id = match_id
                ans.plagiarism_checked_at = now
                checked += 1
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                "plagiarism_check.failed answer=%s", ans.id
            )

    await db.flush()
    return checked

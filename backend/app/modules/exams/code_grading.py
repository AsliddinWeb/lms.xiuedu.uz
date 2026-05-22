"""Code question test case CRUD + run/grade — Phase 9d."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.modules.exams.code_runner import (
    RunResult,
    TestCaseResult,
    compare_output,
    get_runner,
)
from app.modules.exams.models import (
    Answer,
    CodeTestCase,
    Exam,
    ExamAttempt,
    Question,
)


# ---------------------------------------------------------------------------
# Test case CRUD (pedagog)
# ---------------------------------------------------------------------------


async def list_test_cases(
    db: AsyncSession, question_id: int, *, include_hidden: bool = True
) -> list[CodeTestCase]:
    stmt = (
        select(CodeTestCase)
        .where(CodeTestCase.question_id == question_id)
        .order_by(CodeTestCase.order_index.asc(), CodeTestCase.id.asc())
    )
    if not include_hidden:
        stmt = stmt.where(CodeTestCase.is_hidden.is_(False))
    return list((await db.execute(stmt)).scalars().all())


async def _get_question(db: AsyncSession, question_id: int) -> Question:
    q = (
        await db.execute(select(Question).where(Question.id == question_id))
    ).scalar_one_or_none()
    if q is None:
        raise NotFoundError("Savol topilmadi")
    if q.type != "code":
        raise ConflictError("Test case faqat code turi savolda bo'ladi")
    return q


async def create_test_case(
    db: AsyncSession,
    question_id: int,
    *,
    stdin: str,
    expected_stdout: str,
    is_hidden: bool = False,
    weight: float = 1.0,
    order_index: int | None = None,
) -> CodeTestCase:
    await _get_question(db, question_id)
    if order_index is None:
        existing = await list_test_cases(db, question_id)
        order_index = len(existing)
    tc = CodeTestCase(
        question_id=question_id,
        stdin=stdin,
        expected_stdout=expected_stdout,
        is_hidden=is_hidden,
        weight=Decimal(str(weight)),
        order_index=order_index,
    )
    db.add(tc)
    await db.flush()
    return tc


async def update_test_case(
    db: AsyncSession,
    test_case_id: int,
    *,
    stdin: str | None = None,
    expected_stdout: str | None = None,
    is_hidden: bool | None = None,
    weight: float | None = None,
    order_index: int | None = None,
) -> CodeTestCase:
    tc = (
        await db.execute(select(CodeTestCase).where(CodeTestCase.id == test_case_id))
    ).scalar_one_or_none()
    if tc is None:
        raise NotFoundError("Test case topilmadi")
    if stdin is not None:
        tc.stdin = stdin
    if expected_stdout is not None:
        tc.expected_stdout = expected_stdout
    if is_hidden is not None:
        tc.is_hidden = is_hidden
    if weight is not None:
        tc.weight = Decimal(str(weight))
    if order_index is not None:
        tc.order_index = order_index
    await db.flush()
    return tc


async def delete_test_case(db: AsyncSession, test_case_id: int) -> None:
    tc = (
        await db.execute(select(CodeTestCase).where(CodeTestCase.id == test_case_id))
    ).scalar_one_or_none()
    if tc is None:
        raise NotFoundError("Test case topilmadi")
    await db.delete(tc)
    await db.flush()


# ---------------------------------------------------------------------------
# Run code (talaba "Run code" tugmasi) — faqat visible test case'lar
# ---------------------------------------------------------------------------


async def run_code_against_visible(
    db: AsyncSession,
    *,
    attempt_id: int,
    user_id: int,
    question_id: int,
    code: str,
) -> list[TestCaseResult]:
    attempt = (
        await db.execute(select(ExamAttempt).where(ExamAttempt.id == attempt_id))
    ).scalar_one_or_none()
    if attempt is None:
        raise NotFoundError("Urinish topilmadi")
    if attempt.user_id != user_id:
        raise ForbiddenError("Bu urinish sizga tegishli emas")

    question = await _get_question(db, question_id)
    cases = await list_test_cases(db, question_id, include_hidden=False)
    if not cases:
        return []

    runner = get_runner()
    results: list[TestCaseResult] = []
    for tc in cases:
        run = await runner.execute(
            language=question.code_language or "python",
            code=code,
            stdin=tc.stdin or "",
        )
        passed = run.exit_code == 0 and compare_output(tc.expected_stdout, run.stdout)
        results.append(
            TestCaseResult(
                test_case_id=tc.id,
                is_hidden=tc.is_hidden,
                passed=passed,
                run=run,
                expected_stdout=tc.expected_stdout,
            )
        )
    return results


# ---------------------------------------------------------------------------
# Auto-grade — submit paytida barcha test case'lar (hidden ham)
# ---------------------------------------------------------------------------


async def grade_code_answer(
    db: AsyncSession, answer: Answer, question: Question
) -> tuple[Decimal, list[TestCaseResult]]:
    """Kod javobni barcha test case'lar bilan baholaydi.

    Returns (points_earned, results). Hidden + visible barcha test'lar ishlatiladi.
    """
    code = answer.code_answer or ""
    if not code.strip():
        return Decimal("0"), []
    cases = await list_test_cases(db, question.id, include_hidden=True)
    if not cases:
        # Test case yo'q — manual grading kerak
        return Decimal("0"), []

    runner = get_runner()
    results: list[TestCaseResult] = []
    total_weight = Decimal("0")
    earned_weight = Decimal("0")
    for tc in cases:
        run = await runner.execute(
            language=question.code_language or "python",
            code=code,
            stdin=tc.stdin or "",
        )
        passed = run.exit_code == 0 and compare_output(tc.expected_stdout, run.stdout)
        w = Decimal(str(tc.weight))
        total_weight += w
        if passed:
            earned_weight += w
        results.append(
            TestCaseResult(
                test_case_id=tc.id,
                is_hidden=tc.is_hidden,
                passed=passed,
                run=run,
                expected_stdout=tc.expected_stdout,
            )
        )

    if total_weight == 0:
        return Decimal("0"), results
    fraction = earned_weight / total_weight
    points = (question.points * fraction).quantize(Decimal("0.01"))
    return points, results

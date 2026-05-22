"""Phase 7c — retry_async unit testlari."""

from __future__ import annotations

import pytest

from app.integrations.hemis.retry import retry_async


@pytest.mark.asyncio
async def test_succeeds_first_attempt():
    counter = {"n": 0}

    async def task():
        counter["n"] += 1
        return "ok"

    result = await retry_async(task, attempts=3, backoff_seconds=(0, 0, 0))
    assert result == "ok"
    assert counter["n"] == 1


@pytest.mark.asyncio
async def test_succeeds_after_failures():
    counter = {"n": 0}

    async def flaky():
        counter["n"] += 1
        if counter["n"] < 3:
            raise RuntimeError("transient")
        return "ok"

    result = await retry_async(flaky, attempts=3, backoff_seconds=(0, 0, 0))
    assert result == "ok"
    assert counter["n"] == 3


@pytest.mark.asyncio
async def test_raises_after_all_attempts():
    counter = {"n": 0}

    async def always_fails():
        counter["n"] += 1
        raise ValueError(f"fail-{counter['n']}")

    with pytest.raises(ValueError, match="fail-3"):
        await retry_async(always_fails, attempts=3, backoff_seconds=(0, 0, 0))
    assert counter["n"] == 3


@pytest.mark.asyncio
async def test_retry_on_filter():
    counter = {"n": 0}

    async def task():
        counter["n"] += 1
        raise TypeError("not retryable")

    # TypeError not in retry_on tuple → no retry
    with pytest.raises(TypeError):
        await retry_async(
            task,
            attempts=3,
            backoff_seconds=(0, 0, 0),
            retry_on=(ValueError,),
        )
    assert counter["n"] == 1

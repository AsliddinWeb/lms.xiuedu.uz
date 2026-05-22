"""Code runner — Phase 9d.

Talaba kodi sandbox'da ishlatib, stdout natijasini qaytaradi. Default `mock`
runner — haqiqiy bajarish yo'q, faqat exact match qaytaradi (dev). Production
uchun **Piston** (engineer-man/piston) Docker container:

    POST {PISTON_URL}/api/v2/execute
    body: {language, version, files:[{content}], stdin, run_timeout, run_memory_limit}

Sozlamalar:
    CODE_RUNNER_PROVIDER  ('mock' | 'piston')   default: mock
    PISTON_URL            (mavjud bo'lsa)         default: http://piston:2000
    CODE_RUN_TIMEOUT_MS   default: 3000
    CODE_RUN_MEMORY_MB    default: 256
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# Til nomi → Piston'dagi til + version
LANGUAGE_MAP: dict[str, tuple[str, str]] = {
    "python": ("python", "3.10.0"),
    "javascript": ("javascript", "18.15.0"),
    "js": ("javascript", "18.15.0"),
    "typescript": ("typescript", "5.0.3"),
    "ts": ("typescript", "5.0.3"),
    "java": ("java", "15.0.2"),
    "c": ("c", "10.2.0"),
    "cpp": ("c++", "10.2.0"),
    "c++": ("c++", "10.2.0"),
    "go": ("go", "1.16.2"),
    "rust": ("rust", "1.68.2"),
    "php": ("php", "8.2.3"),
    "ruby": ("ruby", "3.0.1"),
    "swift": ("swift", "5.3.3"),
    "kotlin": ("kotlin", "1.8.20"),
}


@dataclass
class RunResult:
    """Bir test case uchun ishga tushirish natijasi."""

    stdout: str
    stderr: str
    exit_code: int
    runtime_ms: int
    timed_out: bool
    error: str | None = None


@dataclass
class TestCaseResult:
    """Test case'ni baholash natijasi."""

    test_case_id: int
    is_hidden: bool
    passed: bool
    run: RunResult
    expected_stdout: str


class MockRunner:
    """Dev mock — kodni bajarmaydi, stdout sifatida bo'sh string qaytaradi.

    Hozirgi maqsadi: backend infrastruktura tayyor turishi. Production'da
    PISTON_URL berib Piston'ga ulanish kerak.
    """

    provider: Literal["mock"] = "mock"

    async def execute(
        self,
        *,
        language: str,
        code: str,
        stdin: str,
        timeout_ms: int = 3000,
        memory_mb: int = 256,
    ) -> RunResult:
        # Mock doim "executed" qaytaradi — auto-grade mock natijasiz manual qoladi
        return RunResult(
            stdout="",
            stderr="(code-runner: mock provider — real runner kerak)",
            exit_code=0,
            runtime_ms=0,
            timed_out=False,
            error="mock_provider",
        )


class PistonRunner:
    """Piston HTTP client (engineer-man/piston)."""

    provider: Literal["piston"] = "piston"

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def execute(
        self,
        *,
        language: str,
        code: str,
        stdin: str,
        timeout_ms: int = 3000,
        memory_mb: int = 256,
    ) -> RunResult:
        lang_key = LANGUAGE_MAP.get(language.lower())
        if lang_key is None:
            return RunResult(
                stdout="",
                stderr=f"unsupported language: {language}",
                exit_code=1,
                runtime_ms=0,
                timed_out=False,
                error="unsupported_language",
            )
        piston_lang, version = lang_key

        body = {
            "language": piston_lang,
            "version": version,
            "files": [{"content": code}],
            "stdin": stdin,
            "run_timeout": timeout_ms,
            "run_memory_limit": memory_mb * 1024 * 1024,
        }
        try:
            async with httpx.AsyncClient(timeout=(timeout_ms / 1000.0) + 5) as client:
                r = await client.post(f"{self.base_url}/api/v2/execute", json=body)
            if r.status_code != 200:
                return RunResult(
                    stdout="",
                    stderr=f"piston error {r.status_code}: {r.text[:200]}",
                    exit_code=1,
                    runtime_ms=0,
                    timed_out=False,
                    error=f"piston_http_{r.status_code}",
                )
            data = r.json()
            run = data.get("run") or {}
            return RunResult(
                stdout=str(run.get("stdout") or ""),
                stderr=str(run.get("stderr") or ""),
                exit_code=int(run.get("code") or 0),
                runtime_ms=int(run.get("time", 0) * 1000),
                timed_out=run.get("signal") == "SIGKILL",
            )
        except httpx.TimeoutException:
            return RunResult(
                stdout="", stderr="execution timed out", exit_code=124,
                runtime_ms=timeout_ms, timed_out=True, error="timeout",
            )
        except Exception as e:
            logger.exception("piston.execute_failed")
            return RunResult(
                stdout="", stderr=str(e)[:200], exit_code=1,
                runtime_ms=0, timed_out=False, error="exception",
            )


def get_runner() -> MockRunner | PistonRunner:
    """Singleton runner — settings'ga qarab tanlanadi."""
    provider = getattr(settings, "CODE_RUNNER_PROVIDER", "mock")
    if provider == "piston":
        url = getattr(settings, "PISTON_URL", "") or "http://piston:2000"
        return PistonRunner(url)
    return MockRunner()


def compare_output(expected: str, actual: str) -> bool:
    """Whitespace-insensitive comparison (newline norm + trailing trim)."""
    def norm(s: str) -> str:
        return "\n".join(line.rstrip() for line in s.replace("\r\n", "\n").split("\n")).rstrip()
    return norm(expected) == norm(actual)

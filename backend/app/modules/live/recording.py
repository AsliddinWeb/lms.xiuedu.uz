"""Recording yordamchi util'lari — ffmpeg/ffprobe (graceful fallback).

Phase 5d: agar ffmpeg/ffprobe konteynerda bo'lmasa, funksiyalar None qaytaradi
va recording upload baribir muvaffaqiyatli yakunlanadi (faqat thumbnail va
duration metadata yo'q bo'ladi).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

# Qabul qilinadigan video formatlar — Jibri va brauzerda yozilgan asosiy formatlar
ALLOWED_RECORDING_MIME = {
    "video/mp4",
    "video/webm",
    "video/x-matroska",  # .mkv
    "video/quicktime",  # .mov
}

# Faylga oddiy hard cap (FastAPI ham bu darajada accept qiladi). Streaming
# upload kelajakda implement qilinishi mumkin — hozircha lecture recording
# uchun 2 GB yetarli.
RECORDING_HARD_MAX_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB


def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def has_ffprobe() -> bool:
    return shutil.which("ffprobe") is not None


def probe_duration_seconds(file_path: str | Path) -> int | None:
    """Video davomiyligini sekundlarda qaytaradi (ffprobe orqali). Xato bo'lsa None."""
    if not has_ffprobe():
        return None
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            logger.warning("ffprobe.failed", stderr=result.stderr[:200])
            return None
        data = json.loads(result.stdout)
        duration = float(data.get("format", {}).get("duration", 0))
        return int(duration) if duration > 0 else None
    except (subprocess.TimeoutExpired, json.JSONDecodeError, ValueError) as exc:
        logger.warning("ffprobe.error", error=str(exc))
        return None


def generate_thumbnail(file_path: str | Path) -> bytes | None:
    """Video'dan 1 ta JPEG thumbnail (5-soniyadan) qaytaradi. Xato → None.

    Output: 640x360 JPEG byte'lari (oddiy lecture poster uchun yetarli).
    """
    if not has_ffmpeg():
        return None
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                "5",  # 5-soniyaga seek (boshida qora frame ehtimoli)
                "-i",
                str(file_path),
                "-frames:v",
                "1",
                "-vf",
                "scale=640:-2",
                "-q:v",
                "3",
                tmp_path,
            ],
            capture_output=True,
            timeout=60,
            check=False,
        )
        if result.returncode != 0:
            logger.warning("ffmpeg.thumbnail_failed", stderr=result.stderr[:200].decode("utf-8", "ignore"))
            return None
        data = Path(tmp_path).read_bytes()
        return data if data else None
    except subprocess.TimeoutExpired:
        logger.warning("ffmpeg.thumbnail_timeout")
        return None
    finally:
        Path(tmp_path).unlink(missing_ok=True)

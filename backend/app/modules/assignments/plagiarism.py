"""Plagiat tekshiruvi (Phase 4e — mock client).

TZ § 07-assignments § 6: Antiplag.uz integratsiyasi (asosiy), Turnitin (xalqaro,
ixtiyoriy). Hozircha mock client — deterministik (testlarda baholash mumkin)
va keyingi sub-faza'da real Antiplag API bilan almashtiriladi.

Mock algoritm:
- Matn uzunligi 0 → 0%
- Hash(text) ning quyi 7 bitiga teng (0..127) ni 100 ga normalize → 0..78%
  Buyni ishlatish — har xil submissionlar har xil natija beradi, lekin har
  yangidan tekshiruv bir xil natija beradi (idempotent test uchun ham).
- Bo'sh content (faqat fayl) → fayl nomlari hashidan olinadi.
- `report_url` mock URL: `https://antiplag.local/reports/{submission_id}`

Real integratsiya kelajak Phase'da:
- `app/integrations/antiplag/client.py` (httpx async)
- Celery task `check_plagiarism_async` — large submissionlar uchun
- Webhook callback URL'i bilan natija qabul qilish
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class PlagiarismResult:
    """Plagiat tekshiruvi natijasi."""

    similarity_percent: Decimal
    report_url: str
    sources: list[dict]  # [{name, similarity, url}, ...]


def _hash_score(text: str) -> Decimal:
    """Determinstik mock score (0..78%) — testlarda barqaror natija."""
    if not text:
        return Decimal("0")
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    raw = digest[0] & 0x7F  # 0..127
    pct = (Decimal(raw) / Decimal("127") * Decimal("78")).quantize(Decimal("0.01"))
    return pct


def check_text(text: str, *, submission_id: int) -> PlagiarismResult:
    """Bitta matn uchun mock tekshiruv.

    Real implementatsiyada bu funktsiya Antiplag.uz API'ni chaqiradi va
    similarity_percent + manbalar ro'yxatini qaytaradi.
    """
    score = _hash_score(text)
    sources: list[dict] = []
    if score >= Decimal("10"):
        sources.append(
            {
                "name": "mock-source-1",
                "similarity": str(score / Decimal("2")),
                "url": "https://antiplag.local/sources/1",
            }
        )
    return PlagiarismResult(
        similarity_percent=score,
        report_url=f"https://antiplag.local/reports/{submission_id}",
        sources=sources,
    )


def check_submission(
    *, submission_id: int, content: str | None, files: list[dict]
) -> PlagiarismResult:
    """Submission uchun: agar content bo'lsa shuni tekshiradi, aks holda
    fayl nomlari + fayl size'larini birlashtirib hash qiladi.
    """
    if content and content.strip():
        return check_text(content, submission_id=submission_id)
    file_signature = "|".join(
        f"{f.get('name', '')}:{f.get('size', 0)}" for f in (files or [])
    )
    return check_text(file_signature, submission_id=submission_id)

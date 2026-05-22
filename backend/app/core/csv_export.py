"""CSV export helpers — Phase 8f.

Admin/pedagog ko'p sahifada "Export CSV" tugmasiga ega bo'ladi. Bu modul
oddiy `rows → CSV bytes` konvertorlari beradi. Headers va data row'lar
list[dict] sifatida keladi.

Foydalanish:
    csv_bytes = rows_to_csv(
        ["id", "name", "email"],
        [{"id": 1, "name": "Ali", "email": "ali@x.uz"}],
    )
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={fname}.csv"},
    )

BOM (\\ufeff) qo'shiladi — Excel uchun (UTF-8 boldlash). Aks holda kirill
matn buzilib ko'rinadi.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable
from typing import Any


def rows_to_csv(
    headers: list[str],
    rows: Iterable[dict[str, Any]],
    *,
    delimiter: str = ",",
    bom: bool = True,
) -> str:
    """`headers` ustun nomlari, `rows` dict listi.

    Yo'q bo'lgan kalitlar uchun bo'sh string yoziladi. None ham bo'sh string.
    """
    buf = io.StringIO()
    if bom:
        # Excel UTF-8 ni avtomatik aniqlashi uchun BOM kerak (ayniqsa kirill).
        buf.write("﻿")
    writer = csv.writer(buf, delimiter=delimiter, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(["" if row.get(h) is None else row[h] for h in headers])
    return buf.getvalue()


def filename_with_timestamp(prefix: str) -> str:
    """`students_20260520_142500.csv` ko'rinishida fayl nomi qaytaradi."""
    from datetime import datetime

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}.csv"

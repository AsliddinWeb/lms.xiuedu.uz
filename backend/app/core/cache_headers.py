"""HTTP cache headers helpers — Phase 8c.

Backend authenticated API uchun "shared" public CDN cache yaroqsiz —
har response privatecache (per user). Lekin **list endpoint'lari** uchun
qisqa muddatli private cache foydali:

  - Kuza-kuza akademik resurslar (kafedralar, fakultetlar, fanlar) — kamdan
    o'zgaradi, browser 30-60s saqlasa, frontend bir necha sahifa orasida
    qayta fetch qilmaydi.
  - Kurs ro'yxati — kamroq, lekin "primary author" sahifalashda dam
    qiladi.

Endpoint'da response parameter sifatida `Response` qabul qilib, fn boshida
chaqirish kifoya:

    @router.get("/faculties")
    async def list_faculties(response: Response, ...):
        cache_private(response, seconds=60)
        ...

Authenticated user uchun ETag berishni o'rniga `Cache-Control: private`
yetarli — proxy/CDN keshlamaydi, faqat brauzer keshlaydi.
"""

from __future__ import annotations

from starlette.responses import Response


def cache_private(response: Response, *, seconds: int = 60) -> None:
    """Brauzerga `seconds` davomida shu user uchun response saqlash imkonini beradi.

    `private` — proxy/CDN keshlamaydi.
    `max-age` — brauzer fresh deb hisoblaydi shu vaqt davomida.
    `must-revalidate` — ekspire bo'lgach 304 uchun qayta tekshiradi.
    """
    response.headers["Cache-Control"] = (
        f"private, max-age={seconds}, must-revalidate"
    )


def no_store(response: Response) -> None:
    """Sensitive endpoint'lar uchun: hech qaerda keshlanmasin."""
    response.headers["Cache-Control"] = "no-store"

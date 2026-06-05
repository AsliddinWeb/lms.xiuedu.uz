"""Sertifikat PDF + QR kod generator — professional kreativ dizayn.

A4 landscape, navy + gold brend, klassik tipografiya (Times), burchak bezaklari,
rasmiy muhr (medallion), imzo joylari va QR (public verify).

`organization_name` MAJBURIY — chaqiruvchi uni DB'dagi Organization yozuvidan
(adminka orqali tahrirlanadigan) uzatadi. Hech qayerda hardcode emas.
"""

from __future__ import annotations

import io
import math
from datetime import datetime

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.pdfgen.canvas import Canvas

NAVY = colors.HexColor("#1f3a5f")
NAVY_DEEP = colors.HexColor("#16314f")
GOLD = colors.HexColor("#b8923c")
GOLD_LT = colors.HexColor("#d9b962")
GOLD_SOFT = colors.HexColor("#efe1ba")
INK = colors.HexColor("#1f2937")
GRAY = colors.HexColor("#6b7280")
GRAY_SOFT = colors.HexColor("#9ca3af")


def _qr_image(data: str) -> pdf_canvas.ImageReader:
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=1)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1f3a5f", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return pdf_canvas.ImageReader(buf)


def _star(c: Canvas, cx: float, cy: float, outer: float, inner: float) -> None:
    p = c.beginPath()
    for i in range(10):
        r = outer if i % 2 == 0 else inner
        ang = math.pi / 2 + i * math.pi / 5
        x = cx + r * math.cos(ang)
        y = cy + r * math.sin(ang)
        (p.moveTo if i == 0 else p.lineTo)(x, y)
    p.close()
    c.drawPath(p, stroke=0, fill=1)


def _corner(c: Canvas, x: float, y: float, dx: int, dy: int, size: float) -> None:
    c.line(x, y, x + dx * size, y)
    c.line(x, y, x, y + dy * size)
    c.line(x + dx * 2 * mm, y + dy * 2 * mm, x + dx * (size * 0.6), y + dy * 2 * mm)
    c.line(x + dx * 2 * mm, y + dy * 2 * mm, x + dx * 2 * mm, y + dy * (size * 0.6))


def _divider(c: Canvas, cx: float, y: float, half: float) -> None:
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.9)
    c.line(cx - half, y, cx - 5 * mm, y)
    c.line(cx + 5 * mm, y, cx + half, y)
    c.setFillColor(GOLD)
    p = c.beginPath()
    p.moveTo(cx, y + 2 * mm)
    p.lineTo(cx + 2.4 * mm, y)
    p.lineTo(cx, y - 2 * mm)
    p.lineTo(cx - 2.4 * mm, y)
    p.close()
    c.drawPath(p, stroke=0, fill=1)


def _seal(c: Canvas, cx: float, cy: float, r: float) -> None:
    """Rasmiy muhr — oltin medallion (halqa + yulduz + XIU)."""
    c.setFillColor(GOLD_SOFT)
    c.setStrokeColor(GOLD)
    c.setLineWidth(2.2)
    c.circle(cx, cy, r, stroke=1, fill=1)
    c.setLineWidth(0.7)
    c.setStrokeColor(GOLD)
    c.circle(cx, cy, r - 2.6 * mm, stroke=1, fill=0)
    c.setFillColor(GOLD)
    _star(c, cx, cy + 4.4 * mm, 5 * mm, 2.1 * mm)
    c.setFillColor(NAVY)
    c.setFont("Times-Bold", 12)
    c.drawCentredString(cx, cy - 5.4 * mm, "XIU")
    # pastki lenta
    c.setFillColor(GOLD)
    for dx in (-r * 0.5, r * 0.5):
        p = c.beginPath()
        p.moveTo(cx + dx - 3.4 * mm, cy - r + 1 * mm)
        p.lineTo(cx + dx + 3.4 * mm, cy - r + 1 * mm)
        p.lineTo(cx + dx, cy - r - 5.5 * mm)
        p.close()
        c.drawPath(p, stroke=0, fill=1)


def _signature(c: Canvas, cx: float, y: float, label: str) -> None:
    c.setStrokeColor(GRAY_SOFT)
    c.setLineWidth(0.6)
    c.line(cx - 26 * mm, y, cx + 26 * mm, y)
    c.setFont("Times-Roman", 9.5)
    c.setFillColor(GRAY)
    c.drawCentredString(cx, y - 5 * mm, label)


def render_certificate_pdf(
    *,
    student_name: str,
    course_title: str,
    certificate_number: str,
    issued_at: datetime,
    verification_url: str,
    organization_name: str,
    score_percentage: float | None = None,
) -> bytes:
    buf = io.BytesIO()
    width, height = landscape(A4)
    c = Canvas(buf, pagesize=landscape(A4))
    c.setTitle(f"Sertifikat {certificate_number}")
    c.setAuthor(organization_name)

    cx = width / 2

    # --- Ramkalar ---
    m1 = 11 * mm
    c.setStrokeColor(NAVY)
    c.setLineWidth(1.6)
    c.rect(m1, m1, width - 2 * m1, height - 2 * m1)
    m2 = 14.5 * mm
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.7)
    c.rect(m2, m2, width - 2 * m2, height - 2 * m2)

    # Burchak bezaklari (gold)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.1)
    o = 18 * mm
    _corner(c, m2 + 2 * mm, m2 + 2 * mm, 1, 1, o)
    _corner(c, width - m2 - 2 * mm, m2 + 2 * mm, -1, 1, o)
    _corner(c, m2 + 2 * mm, height - m2 - 2 * mm, 1, -1, o)
    _corner(c, width - m2 - 2 * mm, height - m2 - 2 * mm, -1, -1, o)

    top = height - m2

    # --- OTM nomi (adminkadan) ---
    c.setFillColor(NAVY)
    c.setFont("Times-Bold", 15)
    c.drawCentredString(cx, top - 14 * mm, organization_name)
    c.setFont("Helvetica", 8.5)
    c.setFillColor(GRAY)
    c.drawCentredString(cx, top - 19.5 * mm, "MASOFAVIY TA'LIM PLATFORMASI")

    # --- Title ---
    c.setFillColor(NAVY)
    c.setFont("Times-Bold", 40)
    c.drawCentredString(cx, top - 38 * mm, "SERTIFIKAT")
    _divider(c, cx, top - 43 * mm, 52 * mm)

    # --- Recital ---
    c.setFont("Times-Italic", 12)
    c.setFillColor(GRAY)
    c.drawCentredString(cx, top - 54 * mm, "Ushbu hujjat bilan tasdiqlanadiki,")

    # --- Talaba ismi ---
    c.setFillColor(NAVY)
    c.setFont("Times-Bold", 28)
    c.drawCentredString(cx, top - 70 * mm, student_name)
    c.setStrokeColor(GOLD_LT)
    c.setLineWidth(0.5)
    nlw = 120 * mm
    c.line(cx - nlw / 2, top - 74 * mm, cx + nlw / 2, top - 74 * mm)

    # --- Kurs ---
    c.setFont("Times-Roman", 12.5)
    c.setFillColor(GRAY)
    c.drawCentredString(cx, top - 84 * mm, "quyidagi o'quv kursini muvaffaqiyatli tamomladi:")
    c.setFillColor(INK)
    c.setFont("Times-Bold", 18)
    c.drawCentredString(cx, top - 94 * mm, course_title)

    # --- Yakuniy natija ---
    if score_percentage is not None:
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(cx, top - 104 * mm, f"Yakuniy natija:  {score_percentage:.1f}%")

    # --- Imzo joylari + rasmiy muhr ---
    sig_y = m2 + 30 * mm
    _signature(c, cx - 62 * mm, sig_y, "Rektor")
    _signature(c, cx + 62 * mm, sig_y, "Dekan")
    _seal(c, cx, sig_y + 4 * mm, 13 * mm)

    # --- Pastki strip: raqam/sana (chap), tekshirish (markaz) ---
    fy = m2 + 9 * mm
    c.setFont("Helvetica", 8.5)
    c.setFillColor(GRAY)
    c.drawString(m2 + 8 * mm, fy + 3.5 * mm, f"Sertifikat raqami:  {certificate_number}")
    c.drawString(m2 + 8 * mm, fy - 3 * mm, f"Berilgan sana:  {issued_at.strftime('%d.%m.%Y')}")
    c.setFillColor(GRAY_SOFT)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(cx, fy - 3 * mm, f"Haqiqiyligini tekshirish:  {verification_url}")

    # --- QR (o'ng pastda) ---
    qr_size = 28 * mm
    qr_x = width - m2 - 8 * mm - qr_size
    qr_y = m2 + 8 * mm
    c.drawImage(_qr_image(verification_url), qr_x, qr_y, width=qr_size, height=qr_size, preserveAspectRatio=True)
    c.setFont("Helvetica", 7)
    c.setFillColor(GRAY_SOFT)
    c.drawCentredString(qr_x + qr_size / 2, qr_y - 3.5 * mm, "QR — tekshirish")

    c.showPage()
    c.save()
    return buf.getvalue()

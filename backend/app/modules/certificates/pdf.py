"""Sertifikat PDF + QR kod generator — Phase 11d / 27 (kreativ dizayn).

A4 landscape, navy + gold brend aksenti, oltin medallion (yulduz) seal,
talaba ismi, kurs nomi, ball, imzo joylari va QR kod (public verify).

PDF baytlar bo'lib qaytadi — chaqiruvchi uni MinIO'ga yuklaydi.
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
NAVY_SOFT = colors.HexColor("#33567f")
GOLD = colors.HexColor("#c19a3e")
GOLD_SOFT = colors.HexColor("#e7d3a1")
GRAY = colors.HexColor("#6b7280")
GRAY_SOFT = colors.HexColor("#9ca3af")


def _draw_qr(c: Canvas, data: str, x: float, y: float, size: float) -> None:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1f3a5f", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    c.drawImage(
        image=pdf_canvas.ImageReader(buf),
        x=x,
        y=y,
        width=size,
        height=size,
        preserveAspectRatio=True,
    )


def _star(c: Canvas, cx: float, cy: float, outer: float, inner: float) -> None:
    """5 qirrali yulduz (to'ldirilgan)."""
    p = c.beginPath()
    for i in range(10):
        r = outer if i % 2 == 0 else inner
        ang = math.pi / 2 + i * math.pi / 5
        x = cx + r * math.cos(ang)
        y = cy + r * math.sin(ang)
        if i == 0:
            p.moveTo(x, y)
        else:
            p.lineTo(x, y)
    p.close()
    c.drawPath(p, stroke=0, fill=1)


def _draw_seal(c: Canvas, cx: float, cy: float, r: float) -> None:
    """Oltin medallion: tashqi/ichki halqa + yulduz + 'XIU'."""
    c.setFillColor(GOLD_SOFT)
    c.setStrokeColor(GOLD)
    c.setLineWidth(2.0)
    c.circle(cx, cy, r, stroke=1, fill=1)
    c.setLineWidth(0.8)
    c.circle(cx, cy, r - 3 * mm, stroke=1, fill=0)
    # Yulduz (tepada)
    c.setFillColor(GOLD)
    _star(c, cx, cy + 5 * mm, 6 * mm, 2.6 * mm)
    # 'XIU' matni
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(cx, cy - 6 * mm, "XIU")
    # Pastki lenta (ikki uchburchak)
    c.setFillColor(GOLD)
    for dx in (-r * 0.55, r * 0.55):
        p = c.beginPath()
        p.moveTo(cx + dx - 4 * mm, cy - r + 1 * mm)
        p.lineTo(cx + dx + 4 * mm, cy - r + 1 * mm)
        p.lineTo(cx + dx, cy - r - 6 * mm)
        p.close()
        c.drawPath(p, stroke=0, fill=1)


def render_certificate_pdf(
    *,
    student_name: str,
    course_title: str,
    certificate_number: str,
    issued_at: datetime,
    verification_url: str,
    score_percentage: float | None = None,
    organization_name: str = "Xalqaro innovatsion universiteti",
) -> bytes:
    buf = io.BytesIO()
    page_size = landscape(A4)
    width, height = page_size

    c = Canvas(buf, pagesize=page_size)
    c.setTitle(f"Certificate {certificate_number}")
    c.setAuthor(organization_name)

    # --- Ramka (navy + gold ikki chiziq) ---
    margin = 12 * mm
    c.setStrokeColor(NAVY)
    c.setLineWidth(2.2)
    c.rect(margin, margin, width - 2 * margin, height - 2 * margin)
    inner = margin + 3 * mm
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.8)
    c.rect(inner, inner, width - 2 * inner, height - 2 * inner)

    # --- Tepa brend band ---
    band_h = 16 * mm
    c.setFillColor(NAVY)
    c.rect(inner, height - inner - band_h, width - 2 * inner, band_h, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(inner + 6 * mm, height - inner - 10.5 * mm, "XIU EduPlatform")
    c.setFillColor(GOLD_SOFT)
    c.setFont("Helvetica", 8.5)
    c.drawRightString(
        width - inner - 6 * mm,
        height - inner - 10.5 * mm,
        organization_name.upper(),
    )

    top = height - inner - band_h

    # --- Header tag ---
    c.setFont("Helvetica", 9.5)
    c.setFillColor(GRAY)
    c.drawCentredString(width / 2, top - 13 * mm, "C E R T I F I C A T E   O F   C O M P L E T I O N")

    # --- Title ---
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 34)
    c.drawCentredString(width / 2, top - 27 * mm, "SERTIFIKAT")

    # Gold flourish (title ostida)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.4)
    fl = 50 * mm
    c.line(width / 2 - fl, top - 31 * mm, width / 2 + fl, top - 31 * mm)
    c.setFillColor(GOLD)
    _star(c, width / 2, top - 30.3 * mm, 2.2 * mm, 1.0 * mm)

    # --- Tagline ---
    c.setFont("Helvetica", 11)
    c.setFillColor(GRAY)
    c.drawCentredString(
        width / 2, top - 42 * mm,
        "Quyidagi shaxs ushbu kursni muvaffaqiyatli tugatganini tasdiqlaymiz:",
    )

    # --- Talaba ismi ---
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(width / 2, top - 58 * mm, student_name)
    c.setStrokeColor(GRAY_SOFT)
    c.setLineWidth(0.6)
    lw = 130 * mm
    c.line((width - lw) / 2, top - 62 * mm, (width + lw) / 2, top - 62 * mm)

    # --- Kurs ---
    c.setFont("Helvetica", 11)
    c.setFillColor(GRAY)
    c.drawCentredString(width / 2, top - 72 * mm, "KURS")
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, top - 81 * mm, course_title)

    # --- Ball badge ---
    if score_percentage is not None:
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(
            width / 2, top - 92 * mm, f"Umumiy ko'rsatkich:  {score_percentage:.1f}%"
        )

    # --- Medallion seal (chap pastda) ---
    _draw_seal(c, inner + 30 * mm, margin + 34 * mm, 15 * mm)

    # --- Imzo joylari (markazda) ---
    sig_y = margin + 18 * mm
    for label, sx in (("Rektor", width / 2 - 45 * mm), ("Dekan", width / 2 + 45 * mm)):
        c.setStrokeColor(GRAY_SOFT)
        c.setLineWidth(0.6)
        c.line(sx - 28 * mm, sig_y, sx + 28 * mm, sig_y)
        c.setFont("Helvetica", 9)
        c.setFillColor(GRAY)
        c.drawCentredString(sx, sig_y - 5 * mm, label)

    # --- Footer: raqam + sana (chap), verify (markaz) ---
    c.setFont("Helvetica", 8)
    c.setFillColor(GRAY)
    fy = margin + 8 * mm
    c.drawString(inner + 6 * mm, fy + 3 * mm, f"RAQAM: {certificate_number}")
    c.drawString(inner + 6 * mm, fy - 3 * mm, f"SANA: {issued_at.strftime('%Y-%m-%d')}")
    c.setFillColor(GRAY_SOFT)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(width / 2, fy - 3 * mm, f"Tekshirish: {verification_url}")

    # --- QR (o'ng pastda) ---
    qr_size = 30 * mm
    qr_x = width - inner - 6 * mm - qr_size
    qr_y = margin + 12 * mm
    _draw_qr(c, verification_url, qr_x, qr_y, qr_size)
    c.setFont("Helvetica", 7)
    c.setFillColor(GRAY_SOFT)
    c.drawCentredString(qr_x + qr_size / 2, qr_y - 4 * mm, "QR — tekshirish")

    c.showPage()
    c.save()
    return buf.getvalue()

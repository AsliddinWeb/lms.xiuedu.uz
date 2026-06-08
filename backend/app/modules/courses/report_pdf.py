"""Pedagog hisoboti — brendlangan PDF (Phase 35.2).

A4 portrait: logo + OTM nomi + KPI'lar + baho taqsimoti + kurslar jadvali.
Sertifikat PDF (certificates/pdf.py) helperlari uslubida — reportlab, Times/
Helvetica base14 fontlar, OTM logosi (assets/logo-xiu.webp).
"""

from __future__ import annotations

import io
import os
from datetime import datetime

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.pdfgen.canvas import Canvas

NAVY = colors.HexColor("#16314f")
GOLD = colors.HexColor("#b8923c")
INK = colors.HexColor("#243140")
GRAY = colors.HexColor("#6b7280")
GRAY_SOFT = colors.HexColor("#9aa3af")
LINE = colors.HexColor("#e4e4e7")
MUTED = colors.HexColor("#f4f4f5")

_LOGO_PATH = os.path.join(
    os.path.dirname(__file__), "..", "certificates", "assets", "logo-xiu.webp"
)


def _logo() -> tuple[pdf_canvas.ImageReader, float] | tuple[None, None]:
    try:
        img = Image.open(_LOGO_PATH).convert("RGBA")
        ratio = img.size[0] / img.size[1]
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return pdf_canvas.ImageReader(buf), ratio
    except Exception:  # noqa: BLE001
        return None, None


def _truncate(c: Canvas, text: str, font: str, size: float, max_w: float) -> str:
    c.setFont(font, size)
    if c.stringWidth(text, font, size) <= max_w:
        return text
    ell = "…"
    while text and c.stringWidth(text + ell, font, size) > max_w:
        text = text[:-1]
    return text + ell


def render_teacher_report_pdf(
    *,
    organization_name: str,
    teacher_name: str,
    generated_at: datetime,
    analytics: dict,
) -> bytes:
    buf = io.BytesIO()
    width, height = A4  # portrait
    c = Canvas(buf, pagesize=A4)
    c.setTitle("Pedagog hisoboti")
    c.setAuthor(organization_name)

    LX = 18 * mm
    RX = width - 18 * mm
    y = height - 18 * mm

    # --- Header: logo + OTM nomi + sana/pedagog ---
    logo, ratio = _logo()
    tx = LX
    if logo is not None and ratio:
        lh = 15 * mm
        lw = lh * ratio
        c.drawImage(
            logo, LX, y - lh, width=lw, height=lh, mask="auto", preserveAspectRatio=True
        )
        tx = LX + lw + 6 * mm
    c.setFillColor(NAVY)
    c.setFont("Times-Bold", 15)
    c.drawString(tx, y - 6 * mm, _truncate(c, organization_name, "Times-Bold", 15, RX - tx - 35 * mm))
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 8.5)
    c.drawString(tx, y - 11 * mm, "PEDAGOG HISOBOTI")
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 8.5)
    c.drawRightString(RX, y - 6 * mm, generated_at.strftime("%d.%m.%Y %H:%M"))
    c.drawRightString(RX, y - 11 * mm, _truncate(c, teacher_name, "Helvetica", 8.5, 50 * mm))
    y -= 20 * mm
    c.setStrokeColor(GOLD)
    c.setLineWidth(1)
    c.line(LX, y, RX, y)
    y -= 12 * mm

    # --- KPI qatori ---
    avg = analytics.get("avg_grade")
    kpis = [
        ("Kurslar", str(analytics["total_courses"])),
        ("Talabalar", str(analytics["total_students"])),
        ("Ro'yxatlar", str(analytics["total_enrollments"])),
        ("Tugatish", f'{analytics["completion_rate"]:.0f}%'),
        ("O'rtacha baho", f"{avg:.1f}" if avg is not None else "—"),
    ]
    col_w = (RX - LX) / len(kpis)
    for i, (label, val) in enumerate(kpis):
        cx = LX + i * col_w + col_w / 2
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 19)
        c.drawCentredString(cx, y, val)
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 7)
        c.drawCentredString(cx, y - 6 * mm, label.upper())
    y -= 16 * mm

    # --- Baho taqsimoti ---
    gd = analytics.get("grade_distribution", {})
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(LX, y, "BAHO TAQSIMOTI")
    y -= 6 * mm
    buckets = [
        ("A'lo (86+)", gd.get("excellent", 0)),
        ("Yaxshi (71-85)", gd.get("good", 0)),
        ("Qoniqarli (55-70)", gd.get("satisfactory", 0)),
        ("Qoniqarsiz (<55)", gd.get("fail", 0)),
    ]
    bw = (RX - LX) / 4
    for i, (label, n) in enumerate(buckets):
        cx = LX + i * bw + bw / 2
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 13)
        c.drawCentredString(cx, y - 4 * mm, str(n))
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 7)
        c.drawCentredString(cx, y - 9 * mm, label)
    y -= 16 * mm

    # --- Kurslar jadvali ---
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(LX, y, "KURSLAR BO'YICHA")
    y -= 7 * mm

    # ustun pozitsiyalari
    c_course = LX + 2 * mm
    c_students = LX + 108 * mm
    c_compl = LX + 132 * mm
    c_grade = RX - 2 * mm

    # sarlavha fon
    c.setFillColor(MUTED)
    c.rect(LX, y - 2 * mm, RX - LX, 7 * mm, stroke=0, fill=1)
    c.setFillColor(GRAY)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(c_course, y, "KURS")
    c.drawCentredString(c_students, y, "TALABA")
    c.drawCentredString(c_compl, y, "TUGATISH")
    c.drawRightString(c_grade, y, "BAHO")
    y -= 8 * mm

    c.setFont("Helvetica", 8.5)
    for row in analytics.get("per_course", []):
        if y < 22 * mm:  # yangi sahifa
            c.showPage()
            y = height - 20 * mm
        title = _truncate(c, row["title"], "Helvetica", 8.5, 95 * mm)
        c.setFillColor(INK)
        c.setFont("Helvetica", 8.5)
        c.drawString(c_course, y, title)
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 8)
        c.drawCentredString(c_students, y, str(row["student_count"]))
        c.drawCentredString(c_compl, y, f'{row["completion_rate"]:.0f}%')
        g = row.get("avg_grade")
        c.setFillColor(INK)
        c.drawRightString(c_grade, y, f"{g:.1f}" if g is not None else "—")
        c.setStrokeColor(LINE)
        c.setLineWidth(0.4)
        c.line(LX, y - 2.5 * mm, RX, y - 2.5 * mm)
        y -= 7 * mm

    # --- Footer ---
    c.setFillColor(GRAY_SOFT)
    c.setFont("Helvetica", 7)
    c.drawCentredString(
        width / 2, 12 * mm, f"{organization_name} — masofaviy ta'lim platformasi"
    )

    c.showPage()
    c.save()
    return buf.getvalue()

"""Sertifikat PDF + QR generator — zamonaviy chap-tekislangan dizayn.

Namuna uslubi (Coursera/universitet sertifikati): yuqori chapda logo + OTM nomi,
chapda sana → talaba ismi → kurs → izoh → imzo; o'ng tomonda vertikal tasma
(pennant) ichida rasmiy muhr (arc text + monogram); pastda QR (public verify).

`organization_name` MAJBURIY — chaqiruvchi uni DB'dagi Organization yozuvidan
(adminka orqali tahrirlanadigan) uzatadi. Hech qayerda hardcode emas.
Logo: assets/logo-xiu.webp (adminka kelajakda almashtirishi mumkin).
"""

from __future__ import annotations

import io
import math
import os
from datetime import datetime

import qrcode
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.pdfgen.canvas import Canvas

NAVY = colors.HexColor("#16314f")
NAVY_SOFT = colors.HexColor("#1f3a5f")
GOLD = colors.HexColor("#b8923c")
GOLD_LT = colors.HexColor("#d2ad5c")
INK = colors.HexColor("#243140")
GRAY = colors.HexColor("#6b7280")
GRAY_SOFT = colors.HexColor("#9aa3af")
RIBBON_FILL = colors.HexColor("#eef3f8")
RIBBON_LINE = colors.HexColor("#c9d6e3")

_LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "logo-xiu.webp")

# Uzbek oy nomlari (sana formatlash uchun)
_MONTHS = [
    "",
    "yanvar", "fevral", "mart", "aprel", "may", "iyun",
    "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr",
]


def _fmt_date(dt: datetime) -> str:
    return f"{dt.day}-{_MONTHS[dt.month]}, {dt.year}"


def _logo() -> tuple[pdf_canvas.ImageReader, float] | tuple[None, None]:
    """Logoni o'qiydi -> (ImageReader, w/h nisbati). Topilmasa (None, None)."""
    try:
        img = Image.open(_LOGO_PATH).convert("RGBA")
        ratio = img.size[0] / img.size[1]
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return pdf_canvas.ImageReader(buf), ratio
    except Exception:  # noqa: BLE001
        return None, None


def _qr_image(data: str) -> pdf_canvas.ImageReader:
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=1
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#16314f", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return pdf_canvas.ImageReader(buf)


def _wrap(c: Canvas, text: str, font: str, size: float, max_w: float) -> list[str]:
    c.setFont(font, size)
    lines: list[str] = []
    cur = ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if c.stringWidth(trial, font, size) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _spaced_center(
    c: Canvas, cx: float, y: float, text: str, font: str, size: float, tracking: float
) -> None:
    """Harf oralig'i (tracking) bilan markazga tekislab chizadi."""
    c.setFont(font, size)
    widths = [c.stringWidth(ch, font, size) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = cx - total / 2
    for ch, w in zip(text, widths):
        c.drawString(x, y, ch)
        x += w + tracking


def _star(c: Canvas, cx: float, cy: float, outer: float, inner: float) -> None:
    p = c.beginPath()
    for i in range(10):
        r = outer if i % 2 == 0 else inner
        ang = math.pi / 2 + i * math.pi / 5
        (p.moveTo if i == 0 else p.lineTo)(cx + r * math.cos(ang), cy + r * math.sin(ang))
    p.close()
    c.drawPath(p, stroke=0, fill=1)


def _arc_text(
    c: Canvas,
    cx: float,
    cy: float,
    radius: float,
    text: str,
    start_ang: float,
    end_ang: float,
    font: str,
    size: float,
    *,
    invert: bool = False,
) -> None:
    """Matnni doira yoyiga (tangens) bo'ylab chizadi — muhr halqasi uchun."""
    c.setFont(font, size)
    n = len(text)
    if n == 0:
        return
    span = end_ang - start_ang
    for i, ch in enumerate(text):
        ang = start_ang + span * (i + 0.5) / n
        rad = math.radians(ang)
        x = cx + radius * math.cos(rad)
        y = cy + radius * math.sin(rad)
        c.saveState()
        c.translate(x, y)
        c.rotate(ang + 90 if invert else ang - 90)
        c.drawCentredString(0, 0, ch)
        c.restoreState()


def _corner_bracket(c: Canvas, x: float, y: float, dx: int, dy: int, size: float) -> None:
    c.line(x, y, x + dx * size, y)
    c.line(x, y, x, y + dy * size)


def _seal(c: Canvas, cx: float, cy: float, r: float) -> None:
    """Rasmiy muhr — navy/gold medallion: halqa + arc matn + XIU monogram."""
    # tashqi to'ldirilgan disk (juda och) + halqalar
    c.setFillColor(colors.white)
    c.setStrokeColor(NAVY)
    c.setLineWidth(1.4)
    c.circle(cx, cy, r, stroke=1, fill=1)
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.8)
    c.circle(cx, cy, r - 1.6 * mm, stroke=1, fill=0)
    c.setStrokeColor(NAVY)
    c.setLineWidth(0.6)
    c.circle(cx, cy, r - 6.4 * mm, stroke=1, fill=0)

    # halqa ichidagi arc matn
    c.setFillColor(NAVY)
    _arc_text(c, cx, cy, r - 4.0 * mm, "TA'LIM  HAR  KIM  UCHUN", 152, 28, "Helvetica-Bold", 6.6)
    c.setFillColor(GOLD)
    _arc_text(c, cx, cy, r - 4.0 * mm, "RASMIY  SERTIFIKAT", 208, 332, "Helvetica-Bold", 6.6, invert=True)

    # yon nuqtalar (ajratgich olmoslar)
    c.setFillColor(GOLD)
    for ang in (0, 180):
        rad = math.radians(ang)
        dx, dy = math.cos(rad), math.sin(rad)
        px, py = cx + (r - 4.0 * mm) * dx, cy + (r - 4.0 * mm) * dy
        p = c.beginPath()
        p.moveTo(px, py + 1.1 * mm)
        p.lineTo(px + 1.1 * mm, py)
        p.lineTo(px, py - 1.1 * mm)
        p.lineTo(px - 1.1 * mm, py)
        p.close()
        c.drawPath(p, stroke=0, fill=1)

    # markaz: yulduz + XIU monogram
    c.setFillColor(GOLD)
    _star(c, cx, cy + 3.0 * mm, 3.0 * mm, 1.2 * mm)
    c.setFillColor(NAVY)
    c.setFont("Times-Bold", 15)
    c.drawCentredString(cx, cy - 3.4 * mm, "XIU")


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

    # ---- Geometriya ----
    LX = 24 * mm                       # chap kontent chizig'i
    ribbon_cx = width - 52 * mm        # tasma markazi (o'ng)
    ribbon_half = 24 * mm
    content_right = ribbon_cx - ribbon_half - 12 * mm
    content_w = content_right - LX

    # ---- Yengil ramka belgilari (burchak qavslari + yuqori chiziq) ----
    c.setStrokeColor(RIBBON_LINE)
    c.setLineWidth(0.8)
    c.line(14 * mm, height - 12 * mm, width - 14 * mm, height - 12 * mm)
    c.setStrokeColor(GOLD_LT)
    c.setLineWidth(1.0)
    b = 9 * mm
    _corner_bracket(c, 14 * mm, height - 12 * mm, 1, -1, b)
    _corner_bracket(c, width - 14 * mm, height - 12 * mm, -1, -1, b)
    _corner_bracket(c, 14 * mm, 12 * mm, 1, 1, b)
    _corner_bracket(c, width - 14 * mm, 12 * mm, -1, 1, b)

    # ================= O'NG TASMA (pennant) =================
    rib_top = height - 18 * mm
    rib_body_bottom = 80 * mm
    rib_point = 62 * mm
    c.setFillColor(RIBBON_FILL)
    c.setStrokeColor(RIBBON_LINE)
    c.setLineWidth(1.0)
    p = c.beginPath()
    p.moveTo(ribbon_cx - ribbon_half, rib_top)
    p.lineTo(ribbon_cx + ribbon_half, rib_top)
    p.lineTo(ribbon_cx + ribbon_half, rib_body_bottom)
    p.lineTo(ribbon_cx, rib_point)
    p.lineTo(ribbon_cx - ribbon_half, rib_body_bottom)
    p.close()
    c.drawPath(p, stroke=1, fill=1)
    # tasma ichki ingichka chiziq
    c.setStrokeColor(colors.white)
    c.setLineWidth(0.6)
    c.line(ribbon_cx - ribbon_half + 2.4 * mm, rib_top - 2.4 * mm,
           ribbon_cx + ribbon_half - 2.4 * mm, rib_top - 2.4 * mm)

    # tasma sarlavhasi
    c.setFillColor(NAVY)
    _spaced_center(c, ribbon_cx, rib_top - 14 * mm, "KURS", "Helvetica-Bold", 12, 2.4)
    _spaced_center(c, ribbon_cx, rib_top - 21 * mm, "SERTIFIKATI", "Helvetica-Bold", 12, 2.4)

    # muhr
    _seal(c, ribbon_cx, rib_body_bottom + 36 * mm, 19 * mm)

    # ================= CHAP KONTENT =================
    # --- Logo + OTM nomi (yuqori chap) ---
    logo_reader, ratio = _logo()
    top_y = height - 24 * mm
    name_x = LX
    if logo_reader is not None and ratio:
        logo_h = 22 * mm
        logo_w = logo_h * ratio
        c.drawImage(
            logo_reader, LX, top_y - logo_h, width=logo_w, height=logo_h,
            mask="auto", preserveAspectRatio=True,
        )
        name_x = LX + logo_w + 7 * mm

    # OTM nomi logoning yonida, vertikal markazda (1-2 qator)
    org_lines = _wrap(c, organization_name, "Times-Bold", 17, content_right - name_x)
    line_gap = 7.2 * mm
    block_h = (len(org_lines) - 1) * line_gap
    oy = top_y - 11 * mm + block_h / 2
    c.setFillColor(NAVY)
    c.setFont("Times-Bold", 17)
    for ln in org_lines:
        c.drawString(name_x, oy, ln)
        oy -= line_gap

    # nozik ajratuvchi chiziq logodan past
    c.setStrokeColor(RIBBON_LINE)
    c.setLineWidth(0.7)
    c.line(LX, top_y - 30 * mm, content_right, top_y - 30 * mm)

    # --- Sana ---
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10.5)
    c.drawString(LX, top_y - 41 * mm, _fmt_date(issued_at))

    # --- Talaba ismi (katta serif) ---
    name_lines = _wrap(c, student_name, "Times-Roman", 32, content_w)
    ny = top_y - 53 * mm
    c.setFillColor(NAVY)
    c.setFont("Times-Roman", 32)
    for ln in name_lines:
        c.drawString(LX, ny, ln)
        ny -= 12 * mm
    cur_y = ny + 12 * mm - 13 * mm  # oxirgi qatordan past

    # --- Caption ---
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10.5)
    c.drawString(LX, cur_y, "quyidagi o'quv kursini muvaffaqiyatli tamomladi")
    cur_y -= 11 * mm

    # --- Kurs nomi (serif) ---
    course_lines = _wrap(c, course_title, "Times-Bold", 18, content_w)
    c.setFillColor(INK)
    c.setFont("Times-Bold", 18)
    for ln in course_lines:
        c.drawString(LX, cur_y, ln)
        cur_y -= 8.4 * mm
    cur_y -= 2 * mm

    # --- Izoh + natija ---
    desc = f"{organization_name} tomonidan tashkil etilgan onlayn o'quv kursi"
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 9.5)
    for ln in _wrap(c, desc, "Helvetica", 9.5, content_w):
        c.drawString(LX, cur_y, ln)
        cur_y -= 5.6 * mm
    if score_percentage is not None:
        cur_y -= 1.5 * mm
        c.setFillColor(NAVY_SOFT)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(LX, cur_y, f"Yakuniy natija:  {score_percentage:.0f}%")

    # --- Imzo (pastki chap) ---
    sig_y = 44 * mm
    c.setStrokeColor(GRAY_SOFT)
    c.setLineWidth(0.7)
    c.line(LX, sig_y, LX + 58 * mm, sig_y)
    c.setFillColor(INK)
    c.setFont("Times-Bold", 10.5)
    c.drawString(LX, sig_y - 6 * mm, "Rektor")
    c.setFillColor(GRAY)
    c.setFont("Times-Roman", 9.5)
    c.drawString(LX, sig_y - 11 * mm, organization_name)

    # ================= PASTKI STRIP =================
    # raqam (chap past)
    c.setFillColor(GRAY_SOFT)
    c.setFont("Helvetica", 8.5)
    c.drawString(LX, 22 * mm, f"Sertifikat raqami:  {certificate_number}")

    # QR (o'ng past) + verify matn
    qr_size = 23 * mm
    qr_x = width - 22 * mm - qr_size
    qr_y = 20 * mm
    c.drawImage(_qr_image(verification_url), qr_x, qr_y, width=qr_size, height=qr_size,
                preserveAspectRatio=True)
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 8)
    c.drawRightString(qr_x - 5 * mm, qr_y + qr_size - 7 * mm, "Haqiqiyligini tekshiring:")
    c.setFillColor(NAVY_SOFT)
    c.setFont("Helvetica", 8)
    c.drawRightString(qr_x - 5 * mm, qr_y + qr_size - 12 * mm, verification_url)

    c.showPage()
    c.save()
    return buf.getvalue()

"""Sertifikat PDF + QR kod generator — Phase 11d.

Bitta sahifa A4 landscape PDF — XIU brandi, talaba ismi, kurs nomi,
sertifikat raqami, sana va o'ng pastda QR kod (verification URL'iga).

PDF baytlar bo'lib qaytadi — yuqori darajada chaqiruvchi shu baytni MinIO'ga
upload qiladi.
"""

from __future__ import annotations

import io
from datetime import datetime

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.pdfgen.canvas import Canvas


def _draw_qr(c: Canvas, data: str, x: float, y: float, size: float) -> None:
    """QR kodni reportlab canvas'iga PIL Image orqali joylaydi."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
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


def render_certificate_pdf(
    *,
    student_name: str,
    course_title: str,
    certificate_number: str,
    issued_at: datetime,
    verification_url: str,
    score_percentage: float | None = None,
    organization_name: str = "Xalqaro Innovatsiya Universiteti",
) -> bytes:
    """A4 landscape sahifa, monoxrom, mo'tadil rasmiy ko'rinish."""
    buf = io.BytesIO()
    page_size = landscape(A4)
    width, height = page_size

    c = Canvas(buf, pagesize=page_size)
    c.setTitle(f"Certificate {certificate_number}")
    c.setAuthor(organization_name)

    # Outer border
    margin = 15 * mm
    c.setStrokeColor(colors.black)
    c.setLineWidth(1.0)
    c.rect(margin, margin, width - 2 * margin, height - 2 * margin)

    # Inner thin border
    inner = margin + 4 * mm
    c.setLineWidth(0.4)
    c.rect(inner, inner, width - 2 * inner, height - 2 * inner)

    # Header tag
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#737373"))
    c.drawCentredString(
        width / 2, height - margin - 12 * mm, "CERTIFICATE OF COMPLETION"
    )

    # Title
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width / 2, height - margin - 28 * mm, "SERTIFIKAT")

    # Tagline
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor("#525252"))
    c.drawCentredString(
        width / 2,
        height - margin - 38 * mm,
        "Quyidagi shaxs kursni muvaffaqiyatli tugatganini tasdiqlaydi:",
    )

    # Student name
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width / 2, height - margin - 60 * mm, student_name)

    # Underline beneath name
    c.setStrokeColor(colors.HexColor("#a3a3a3"))
    c.setLineWidth(0.5)
    line_w = 120 * mm
    line_x = (width - line_w) / 2
    c.line(line_x, height - margin - 64 * mm, line_x + line_w, height - margin - 64 * mm)

    # Course title
    c.setFillColor(colors.HexColor("#525252"))
    c.setFont("Helvetica", 12)
    c.drawCentredString(
        width / 2, height - margin - 78 * mm, "Kurs:"
    )
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - margin - 88 * mm, course_title)

    # Score (optional)
    if score_percentage is not None:
        c.setFont("Helvetica", 11)
        c.setFillColor(colors.HexColor("#525252"))
        c.drawCentredString(
            width / 2,
            height - margin - 100 * mm,
            f"Umumiy ko'rsatkich: {score_percentage:.1f}%",
        )

    # Footer left — number + date
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#737373"))
    footer_y = margin + 18 * mm
    c.drawString(inner + 4 * mm, footer_y + 8 * mm, "SERTIFIKAT RAQAMI")
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.black)
    c.drawString(inner + 4 * mm, footer_y + 2 * mm, certificate_number)

    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#737373"))
    c.drawString(inner + 4 * mm, footer_y - 8 * mm, "BERILGAN SANA")
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.black)
    c.drawString(
        inner + 4 * mm,
        footer_y - 14 * mm,
        issued_at.strftime("%Y-%m-%d"),
    )

    # Footer center — organization
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#404040"))
    c.drawCentredString(width / 2, footer_y - 6 * mm, organization_name)
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#a3a3a3"))
    c.drawCentredString(
        width / 2,
        footer_y - 14 * mm,
        f"Tekshirish: {verification_url}",
    )

    # QR code (bottom-right)
    qr_size = 35 * mm
    qr_x = width - inner - 4 * mm - qr_size
    qr_y = footer_y - 18 * mm
    _draw_qr(c, verification_url, qr_x, qr_y, qr_size)
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#a3a3a3"))
    c.drawCentredString(
        qr_x + qr_size / 2, qr_y - 4 * mm, "Skanerlash uchun QR kod"
    )

    c.showPage()
    c.save()
    return buf.getvalue()

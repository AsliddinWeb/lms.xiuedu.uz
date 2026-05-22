"""Email service — Jinja2 templates + async SMTP (Mailhog dev, real SMTP prod).

Spec: docs/03-modules/01-auth.md (verification, reset), docs/03-modules/11-communications.md
"""

from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "emails" / "templates"

_jinja = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
    enable_async=False,
)


def _render(template: str, **ctx: object) -> str:
    return _jinja.get_template(template).render(**ctx)


async def send_email(
    *,
    to: str,
    subject: str,
    html: str,
    text: str | None = None,
    from_addr: str | None = None,
) -> None:
    """SMTP orqali email yuboradi.

    Dev (Mailhog): hostname=mailhog port=1025 (no auth, no TLS).
    Prod: settings.SMTP_HOST/SMTP_PORT, optional auth + TLS.
    """
    if not settings.SMTP_HOST:
        logger.warning("smtp.skip", reason="no_host_configured", to=to, subject=subject)
        return

    msg = EmailMessage()
    msg["From"] = from_addr or settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    if text:
        msg.set_content(text)
        msg.add_alternative(html, subtype="html")
    else:
        msg.set_content(html, subtype="html")

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER or None,
            password=settings.SMTP_PASSWORD or None,
            start_tls=settings.SMTP_USE_TLS,
        )
        logger.info("smtp.sent", to=to, subject=subject)
    except Exception as exc:  # noqa: BLE001
        # Auth/email yiqilsa ham foydalanuvchi flow'i to'xtamasligi kerak.
        # Token DB'da bo'lishi yetarli (admin yordam bera oladi).
        logger.error("smtp.failed", to=to, subject=subject, error=str(exc))


# ---------- High-level helpers ----------


async def send_email_verification(*, to: str, full_name: str, verify_url: str) -> None:
    html = _render("email_verification.html", full_name=full_name, verify_url=verify_url)
    text = _render("email_verification.txt", full_name=full_name, verify_url=verify_url)
    await send_email(
        to=to,
        subject="XIU LMS — Email manzilingizni tasdiqlang",
        html=html,
        text=text,
    )


async def send_password_reset(*, to: str, full_name: str, reset_url: str) -> None:
    html = _render("password_reset.html", full_name=full_name, reset_url=reset_url)
    text = _render("password_reset.txt", full_name=full_name, reset_url=reset_url)
    await send_email(
        to=to,
        subject="XIU LMS — Parolni tiklash",
        html=html,
        text=text,
    )

"""Transactional email delivery — Gmail SMTP and/or Resend."""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, parseaddr

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def email_is_configured() -> bool:
    settings = get_settings()
    return _smtp_ready(settings) or bool((settings.resend_api_key or "").strip())


def _smtp_ready(settings) -> bool:
    return bool(
        (settings.smtp_host or "").strip()
        and (settings.smtp_username or "").strip()
        and (settings.smtp_password or "").strip()
    )


def _from_header(settings) -> str:
    """Prefer SMTP from, then Resend from, then Gmail username."""
    raw = (settings.smtp_from_email or settings.resend_from_email or "").strip()
    if raw:
        return raw
    user = (settings.smtp_username or "").strip()
    if user:
        return formataddr(("BSChat", user))
    return "BSChat <onboarding@resend.dev>"


def _send_smtp_sync(
    *,
    host: str,
    port: int,
    username: str,
    password: str,
    from_header: str,
    to_email: str,
    subject: str,
    html: str,
    text: str | None,
) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_header
    msg["To"] = to_email
    if text:
        msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    _, from_addr = parseaddr(from_header)
    envelope_from = from_addr or username

    with smtplib.SMTP(host, port, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(username, password)
        server.sendmail(envelope_from, [to_email], msg.as_string())


async def send_email(
    *,
    to_email: str,
    subject: str,
    html: str,
    text: str | None = None,
) -> bool:
    """Send one email. Returns False when no provider configured.

    Preference: SMTP (Gmail) when configured, else Resend.
    """
    settings = get_settings()
    provider = (settings.email_provider or "auto").strip().lower()

    use_smtp = _smtp_ready(settings) and provider in ("auto", "smtp")
    use_resend = bool((settings.resend_api_key or "").strip()) and provider in ("auto", "resend")

    if provider == "smtp" and not use_smtp:
        return False
    if provider == "resend" and not use_resend:
        return False

    if use_smtp:
        try:
            await asyncio.to_thread(
                _send_smtp_sync,
                host=settings.smtp_host.strip(),
                port=int(settings.smtp_port),
                username=settings.smtp_username.strip(),
                password=settings.smtp_password,
                from_header=_from_header(settings),
                to_email=to_email,
                subject=subject,
                html=html,
                text=text,
            )
        except Exception:
            logger.exception("SMTP send failed to=%s", to_email)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="EMAIL_SEND_FAILED",
            ) from None
        return True

    if use_resend:
        from_addr = _from_header(settings)
        payload: dict = {
            "from": from_addr,
            "to": [to_email],
            "subject": subject,
            "html": html,
        }
        if text:
            payload["text"] = text
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json=payload,
            )
        if response.status_code >= 400:
            logger.error(
                "Resend send failed status=%s body=%s",
                response.status_code,
                response.text[:300],
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="EMAIL_SEND_FAILED",
            )
        return True

    return False

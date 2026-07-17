"""Unit tests for email provider selection (no network)."""

from app.core import email as email_mod
from app.core.config import get_settings


def test_email_not_configured_by_default(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "resend_api_key", None)
    monkeypatch.setattr(s, "smtp_host", None)
    monkeypatch.setattr(s, "smtp_username", None)
    monkeypatch.setattr(s, "smtp_password", None)
    assert email_mod.email_is_configured() is False


def test_smtp_counts_as_configured(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "resend_api_key", None)
    monkeypatch.setattr(s, "smtp_host", "smtp.gmail.com")
    monkeypatch.setattr(s, "smtp_username", "you@gmail.com")
    monkeypatch.setattr(s, "smtp_password", "app-password")
    assert email_mod.email_is_configured() is True

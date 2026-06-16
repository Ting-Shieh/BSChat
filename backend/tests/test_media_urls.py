"""Media URL normalization tests."""

import pytest

from app.core import media_urls


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_canonical_strips_legacy_localhost(monkeypatch):
    monkeypatch.setenv("API_BASE_URL", "http://localhost:8002")
    assert media_urls.canonical_media_ref(
        "http://localhost:8001/uploads/u1/c1.jpg"
    ) == "/uploads/u1/c1.jpg"


def test_canonical_keeps_external_https(monkeypatch):
    monkeypatch.setenv("API_BASE_URL", "http://localhost:8002")
    url = "https://cdn.example.com/avatar.jpg"
    assert media_urls.canonical_media_ref(url) == url


def test_public_media_url_uses_storage_public_base(monkeypatch):
    monkeypatch.setenv("STORAGE_PUBLIC_BASE_URL", "https://media.example.com")
    monkeypatch.setenv("API_BASE_URL", "http://localhost:8001")
    assert (
        media_urls.public_media_url("/uploads/u1/c1.jpg")
        == "https://media.example.com/uploads/u1/c1.jpg"
    )


def test_public_media_url_legacy_localhost(monkeypatch):
    monkeypatch.setenv("STORAGE_PUBLIC_BASE_URL", "https://media.example.com")
    assert (
        media_urls.public_media_url("http://localhost:8001/uploads/u1/c1.jpg")
        == "https://media.example.com/uploads/u1/c1.jpg"
    )


def test_public_media_url_fallback_to_api_base(monkeypatch):
    monkeypatch.delenv("STORAGE_PUBLIC_BASE_URL", raising=False)
    monkeypatch.delenv("R2_PUBLIC_URL", raising=False)
    monkeypatch.setenv("API_BASE_URL", "http://localhost:8002")
    assert (
        media_urls.public_media_url("/uploads/u1/c1.jpg")
        == "http://localhost:8002/uploads/u1/c1.jpg"
    )

"""Media URL policy: DB stores paths; API returns loadable public URLs from env."""

from app.core.config import get_settings

UPLOADS_PREFIX = "/uploads/"


def media_public_base() -> str:
    """Origin for BSChat-hosted uploads (local /uploads, Neon public_read, or R2 CDN)."""
    settings = get_settings()
    base = settings.storage_public_base_url or settings.r2_public_url or settings.api_base_url
    return base.rstrip("/")


def canonical_media_ref(stored: str | None) -> str | None:
    """Normalize for DB persistence: own uploads → relative /uploads/...; external https unchanged."""
    if not stored:
        return None
    if stored.startswith(("http://", "https://")):
        idx = stored.find(UPLOADS_PREFIX)
        if idx >= 0:
            return stored[idx:]
        return stored
    if stored.startswith(UPLOADS_PREFIX):
        return stored
    return stored


def public_media_url(stored: str | None) -> str | None:
    """API response: full URL for <img src> (legacy localhost stripped via env base)."""
    ref = canonical_media_ref(stored)
    if not ref:
        return None
    if ref.startswith(("http://", "https://")):
        return ref
    if ref.startswith("/"):
        return f"{media_public_base()}{ref}"
    return ref

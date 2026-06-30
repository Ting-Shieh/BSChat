"""Text embeddings for M5 hybrid retrieval (Gemini text-embedding-004)."""

import hashlib
import math

import httpx

from app.core.config import get_settings

settings = get_settings()


def _mock_embedding(text: str, dims: int) -> list[float]:
    """Deterministic pseudo-embedding for tests / offline dev."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    vec = [(digest[i % len(digest)] / 255.0) * 2 - 1 for i in range(dims)]
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in values) + "]"


async def embed_text(text: str) -> list[float] | None:
    """Return embedding vector or None when disabled/unavailable."""
    cleaned = text.strip()
    if not cleaned or not settings.search_embedding_enabled:
        return None

    dims = settings.search_embedding_dims

    if settings.search_embedding_use_mock or not settings.gemini_api_key:
        return _mock_embedding(cleaned, dims)

    model = settings.search_embedding_model
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent"
        f"?key={settings.gemini_api_key}"
    )
    payload = {
        "model": f"models/{model}",
        "content": {"parts": [{"text": cleaned[:8000]}]},
    }
    try:
        async with httpx.AsyncClient(timeout=settings.search_embedding_timeout_s) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            values = data["embedding"]["values"]
            if len(values) != dims:
                return None
            return [float(v) for v in values]
    except Exception:
        return _mock_embedding(cleaned, dims) if settings.search_embedding_fallback_mock else None

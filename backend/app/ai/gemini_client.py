"""Shared Gemini generateContent helper."""

import httpx

from app.core.config import get_settings

settings = get_settings()


async def gemini_generate_text(
    prompt: str,
    *,
    model: str | None = None,
    timeout: float = 60.0,
) -> str:
    api_key = settings.gemini_api_key
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not configured")

    model_name = model or settings.gemini_search_model
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        f"?key={api_key}"
    )
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            url,
            json={"contents": [{"parts": [{"text": prompt}]}]},
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

"""Shared OpenAI Chat Completions helper (search intent / rerank)."""

from __future__ import annotations

import httpx

from app.core.config import get_settings

settings = get_settings()


async def openai_generate_text(
    prompt: str,
    *,
    model: str | None = None,
    timeout: float = 60.0,
) -> str:
    api_key = settings.openai_api_key
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")

    model_name = model or settings.openai_search_model
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_name,
                "temperature": 0,
                "messages": [
                    {
                        "role": "system",
                        "content": "Return JSON only. No markdown fences unless unavoidable.",
                    },
                    {"role": "user", "content": prompt},
                ],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

"""Shared OpenAI Chat Completions helper (search intent / rerank)."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings

settings = get_settings()


async def openai_chat(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    timeout: float = 60.0,
    temperature: float = 0,
    response_format: dict[str, Any] | None = None,
) -> str:
    """OpenAI Chat Completions — pass explicit system / user / assistant roles."""
    api_key = settings.openai_api_key
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")

    model_name = model or settings.openai_search_model
    payload: dict[str, Any] = {
        "model": model_name,
        "temperature": temperature,
        "messages": messages,
    }
    if response_format is not None:
        payload["response_format"] = response_format

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def openai_generate_text(
    prompt: str,
    *,
    model: str | None = None,
    timeout: float = 60.0,
) -> str:
    """Back-compat: single user prompt with a minimal system instruction."""
    return await openai_chat(
        [
            {
                "role": "system",
                "content": "Return JSON only. No markdown fences unless unavoidable.",
            },
            {"role": "user", "content": prompt},
        ],
        model=model,
        timeout=timeout,
    )

"""Shared helpers to mock OpenAI-role intent parsing in tests."""

from __future__ import annotations

from collections.abc import Awaitable, Callable


def patch_intent_llm(monkeypatch, fake_intent: Callable[..., Awaitable[str]]) -> None:
    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_skip_intent_parse", False)
    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_use_mock", False)
    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_provider", "openai")
    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.openai_api_key", "test-key")

    async def _fake_chat(messages, **kwargs):
        prompt = messages[-1]["content"] if isinstance(messages, list) else str(messages)
        return await fake_intent(prompt)

    monkeypatch.setattr("app.ai.pipelines.search_intent.openai_chat", _fake_chat)

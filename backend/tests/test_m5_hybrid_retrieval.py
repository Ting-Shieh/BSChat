"""Unit tests for M5 hybrid retrieval (RRF + semantic query)."""

import uuid

from app.ai.schemas.search_rerank import ParsedIntent
from app.modules.m5_search.hybrid import build_semantic_query, rrf_merge


def test_build_semantic_query_prefers_intent_field():
    intent = ParsedIntent(semantic_query="找 IoT 或物聯網相關的人", keywords=["IoT"])
    assert build_semantic_query(intent, "誰認識做 IOT 的？") == "找 IoT 或物聯網相關的人"


def test_build_semantic_query_fallback_composes_themes():
    intent = ParsedIntent(products=["物聯網"], keywords=["IoT"])
    q = build_semantic_query(intent, "誰認識做 IOT 的？")
    assert "IOT" in q
    assert "物聯網" in q


def test_rrf_merge_boosts_docs_in_multiple_lists():
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    merged = rrf_merge([[a, b, c], [b], [a]])
    scores = dict(merged)
    assert scores[b] > scores[c]


def test_rrf_merge_empty_lists():
    assert rrf_merge([[], []]) == []

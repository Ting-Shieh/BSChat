"""Hybrid retrieval helpers — RRF merge for tsvector + trgm + pgvector."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.ai.schemas.search_rerank import ParsedIntent

RRF_K_DEFAULT = 60


@dataclass
class RetrievalCandidateDebug:
    id: str
    label: str
    retrieval_score: float


@dataclass
class PoolRetrievalDebug:
    pool: str
    lexical_query: str
    semantic_query: str
    ts_hits: int
    trgm_extra_hits: int
    vector_hits: int
    widened: bool
    top_candidates: list[RetrievalCandidateDebug]


def build_semantic_query(intent: ParsedIntent, raw_query: str) -> str:
    """Natural-language string for query embedding."""
    if intent.semantic_query and intent.semantic_query.strip():
        return intent.semantic_query.strip()
    themes = intent.products + intent.roles + intent.keywords
    q = raw_query.strip()
    if themes:
        return f"{q} — {', '.join(themes)}"
    return q


def rrf_merge(
    ranked_lists: list[list[uuid.UUID]],
    *,
    k: int = RRF_K_DEFAULT,
) -> list[tuple[uuid.UUID, float]]:
    """Reciprocal rank fusion across retrieval channels."""
    scores: dict[uuid.UUID, float] = {}
    for ranked in ranked_lists:
        if not ranked:
            continue
        for rank, doc_id in enumerate(ranked, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)

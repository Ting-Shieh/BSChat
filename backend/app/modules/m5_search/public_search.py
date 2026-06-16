"""M5b cross-pool search helpers (Pool A + public directory)."""

import uuid

from app.ai.pipelines.search_rerank import rerank_contacts
from app.ai.schemas.search_rerank import ParsedIntent
from app.modules.m5_search.constraints import filter_rerank_results, has_hard_constraints
from app.modules.m5_search.retrieval import (
    CandidateDoc,
    PublicCandidateDoc,
    public_candidate_to_dict,
    public_to_candidate_doc,
    retrieve_public_candidates,
)
from app.modules.m5_search.validate import validate_rerank_item

ALLOWED_SEARCH_SCOPES = frozenset({"private", "network", "all"})


def can_use_network_scope(plan_tier: str) -> bool:
    return plan_tier in ("pro", "enterprise")


async def rank_public_candidates(
    query_text: str,
    candidates: list[PublicCandidateDoc],
    intent: ParsedIntent,
) -> tuple[list[tuple[object, PublicCandidateDoc]], bool]:
    if not candidates:
        return [], False

    dicts = [public_candidate_to_dict(c) for c in candidates]
    rerank_resp, degraded = await rerank_contacts(query_text, dicts, intent)
    cand_map = {str(c.stub_id): public_to_candidate_doc(c) for c in candidates}

    filtered = filter_rerank_results(rerank_resp.results, cand_map, intent)
    validated: list[tuple[object, PublicCandidateDoc]] = []

    for item in filtered:
        stub_id = item.contact_id
        pc = next((c for c in candidates if str(c.stub_id) == stub_id), None)
        cand_doc = cand_map.get(stub_id)
        if pc and cand_doc and validate_rerank_item(item, cand_doc):
            validated.append((item, pc))

    if not validated and candidates and not has_hard_constraints(intent):
        degraded = True
        for c in sorted(candidates, key=lambda x: x.retrieval_score, reverse=True)[:5]:
            validated.append(
                (
                    type(
                        "R",
                        (),
                        {
                            "contact_id": str(c.stub_id),
                            "match_score": max(c.retrieval_score or 0, 0.35),
                            "match_reason": f"公開商務 · {c.org_name}；{c.display_name} · {c.company_name}",
                            "match_sources": [],
                        },
                    )(),
                    c,
                )
            )

    return validated, degraded

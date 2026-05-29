import uuid

from app.ai.pipelines.search_rerank import _mock_rerank
from app.ai.schemas.search_rerank import ParsedIntent, RerankItem
from app.modules.m5_search.constraints import (
    constraint_matches,
    filter_rerank_results,
    has_hard_constraints,
    satisfies_hard_constraints,
)
from app.modules.m5_search.retrieval import CandidateDoc, build_retrieval_query


def _doc(**kwargs) -> CandidateDoc:
    defaults = dict(
        contact_id=uuid.uuid4(),
        display_name="Test",
        company_name=None,
        title=None,
        responsibility_scope=None,
        responsibility_confidence=None,
        source_label=None,
        review_status="pending_review",
        phones=[],
        emails=[],
        image_url=None,
        company_products=[],
        products_confidence=None,
        search_text="",
        retrieval_score=0.8,
    )
    defaults.update(kwargs)
    return CandidateDoc(**defaults)


def test_build_retrieval_query_includes_hard_fields():
    intent = ParsedIntent(hard_companies=["Amazon"], hard_roles=["架構師"], keywords=["人脈"])
    q = build_retrieval_query(intent, "fallback")
    assert "Amazon" in q
    assert "架構師" in q


def test_constraint_matches_dynamic_terms():
    blob = "program manager amazon web services"
    assert constraint_matches(blob, "amazon")
    assert constraint_matches(blob, "架構師") is False


def test_hard_role_excludes_pm_when_architect_required():
    intent = ParsedIntent(hard_roles=["架構師"], hard_companies=["amazon"])
    pm = _doc(
        title="Program Manager",
        company_name="Amazon Web Services",
        search_text="program manager amazon web services",
    )
    sa = _doc(
        title="資深架構師",
        company_name="Amazon Web Services",
        search_text="資深架構師 amazon web services",
    )
    assert has_hard_constraints(intent)
    assert not satisfies_hard_constraints(pm, intent)
    assert satisfies_hard_constraints(sa, intent)


def test_mock_rerank_hard_architect_only():
    q = "從我AWS人脈中找從事架構師的就好"
    intent = ParsedIntent(hard_roles=["架構師"], hard_companies=["amazon", "亞馬遜"])
    id_pm, id_sa = str(uuid.uuid4()), str(uuid.uuid4())
    cands = [
        {
            "contact_id": id_pm,
            "display_name": "Maggie",
            "title": "Program Manager",
            "company_name": "Amazon Web Services Taiwan Ltd.",
            "search_text": "program manager amazon web services",
            "company_products": [],
            "review_status": "confirmed",
            "retrieval_score": 0.4,
        },
        {
            "contact_id": id_sa,
            "display_name": "王仕榮",
            "title": "資深架構師",
            "company_name": "台灣亞馬遜網路服務有限公司",
            "search_text": "資深架構師 amazon",
            "company_products": ["雲端運算"],
            "review_status": "confirmed",
            "retrieval_score": 0.5,
        },
    ]
    resp = _mock_rerank(q, cands, intent)
    ids = {r.contact_id for r in resp.results}
    assert id_sa in ids
    assert id_pm not in ids


def test_filter_drops_negative_match_reason():
    intent = ParsedIntent(hard_roles=["架構師"], hard_companies=["amazon"])
    cid = str(uuid.uuid4())
    cand = _doc(
        contact_id=uuid.UUID(cid),
        title="Program Manager",
        company_name="Amazon Web Services",
    )
    items = [
        RerankItem(
            contact_id=cid,
            match_score=0.9,
            match_reason="雖在 AWS 任職，但並非架構師",
            match_sources=[],
        )
    ]
    assert filter_rerank_results(items, {cid: cand}, intent) == []

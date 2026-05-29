from app.ai.schemas.search_rerank import RerankItem
from app.modules.m5_search.retrieval import CandidateDoc


def validate_rerank_item(item: RerankItem, candidate: CandidateDoc) -> bool:
    if str(candidate.contact_id) != item.contact_id:
        return False
    for src in item.match_sources:
        if src.field == "company_products" and (candidate.products_confidence or 0) < 0.5:
            return False
        if src.field == "responsibility_scope" and (candidate.responsibility_confidence or 0) < 0.6:
            return False
    return True


def apply_confirmed_boost(score: float, review_status: str) -> float:
    if review_status == "confirmed":
        return min(score * 1.06, 1.0)
    return score

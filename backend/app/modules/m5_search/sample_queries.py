"""DDR-71 / F-5.17: Pro personalized search suggestions from indexed contacts."""

import re
import uuid
from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact
from app.models.contact_search_document import ContactSearchDocument
from app.models.user import User
from app.modules.m5_search.retrieval import _products_for, count_indexed

MAX_SUGGESTIONS = 3
MAX_QUERY_LEN = 120
GENERIC_SOURCE_LABELS = frozenset({"event", "camera_burst", "import", "manual"})


def _is_pro(user: User) -> bool:
    return user.entitlement.plan_tier.lower() == "pro"


def _short_company_name(name: str) -> str:
    lower = name.lower()
    if "amazon" in lower or "aws" in lower or "亞馬遜" in name:
        return "AWS"
    if "google" in lower or "谷歌" in name:
        return "Google"
    if "microsoft" in lower or "微軟" in name:
        return "Microsoft"
    cleaned = re.split(r"(有限公司|Ltd\.?|Inc\.?|Corp\.?)", name, maxsplit=1)[0].strip()
    return cleaned[:16] if len(cleaned) > 16 else cleaned


def _build_queries(
    *,
    products: Counter[str],
    labels: Counter[str],
    companies: Counter[str],
) -> list[str]:
    queries: list[str] = []
    seen: set[str] = set()

    def add(text: str) -> None:
        text = text.strip()
        if not text or text in seen or len(text) > MAX_QUERY_LEN:
            return
        seen.add(text)
        queries.append(text)

    top_product = products.most_common(1)[0][0] if products else None
    top_label = labels.most_common(1)[0][0] if labels else None

    if top_product:
        add(f"我手上有誰做 {top_product} 的？")

    if top_label:
        add(f"{top_label} 認識的人有哪些？")

    if top_product and top_label:
        add(f"在 {top_label} 認識、做 {top_product} 的人")

    for company, count in companies.most_common(3):
        if count >= 2:
            add(f"從 {_short_company_name(company)} 相關人脈中找")

    return queries[:MAX_SUGGESTIONS]


async def pick_sample_queries(db: AsyncSession, user: User) -> list[str]:
    if not _is_pro(user):
        return []

    if await count_indexed(db, user.id) == 0:
        return []

    rows = (
        await db.execute(
            select(
                Contact.company_name,
                Contact.source_label,
                Contact.company_id,
            )
            .join(ContactSearchDocument, ContactSearchDocument.contact_id == Contact.id)
            .where(
                Contact.user_id == user.id,
                Contact.deleted_at.is_(None),
            )
            .limit(50)
        )
    ).all()

    products: Counter[str] = Counter()
    labels: Counter[str] = Counter()
    companies: Counter[str] = Counter()
    seen_company_ids: set[uuid.UUID] = set()

    for company_name, source_label, company_id in rows:
        if company_name and company_name.strip():
            companies[company_name.strip()] += 1

        if source_label:
            label = source_label.strip()
            if label and label.lower() not in GENERIC_SOURCE_LABELS:
                labels[label] += 1

        if company_id and company_id not in seen_company_ids:
            seen_company_ids.add(company_id)
            company_products, conf = await _products_for(db, company_id)
            if (conf or 0) >= 0.5:
                for product in company_products:
                    if product and str(product).strip():
                        products[str(product).strip()] += 1

    return _build_queries(products=products, labels=labels, companies=companies)

"""M11 public directory business logic."""

import csv
import io
import uuid
from datetime import UTC, datetime
from urllib.parse import urlparse

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import OrgMember, Organization
from app.models.public_business_stub import PublicBusinessStub
from app.models.user import User
from app.workers.tasks.public_directory_index import enqueue_stub_index, enqueue_stub_unindex

CSV_HEADERS = (
    "display_name",
    "company_name",
    "title",
    "responsibility_keywords",
    "product_keywords",
    "external_card_url",
)


def validate_external_url(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def _parse_keyword_cell(value: str | None) -> list[str]:
    if not value or not value.strip():
        return []
    return [part.strip() for part in value.replace(";", "|").split("|") if part.strip()]


async def list_user_org_memberships(
    db: AsyncSession, user_id: uuid.UUID
) -> list[tuple[Organization, str]]:
    result = await db.execute(
        select(Organization, OrgMember.role)
        .join(OrgMember, OrgMember.org_id == Organization.id)
        .where(OrgMember.user_id == user_id)
        .order_by(Organization.name)
    )
    return [(row[0], row[1]) for row in result.all()]


async def get_org_summary(db: AsyncSession, org_id: uuid.UUID) -> dict:
    published = await db.scalar(
        select(func.count())
        .select_from(PublicBusinessStub)
        .where(PublicBusinessStub.org_id == org_id, PublicBusinessStub.status == "published")
    )
    return {"published_stub_count": published or 0}


async def list_stubs(
    db: AsyncSession,
    org_id: uuid.UUID,
    *,
    status: str | None = None,
) -> list[PublicBusinessStub]:
    q = select(PublicBusinessStub).where(PublicBusinessStub.org_id == org_id)
    if status:
        q = q.where(PublicBusinessStub.status == status)
    q = q.order_by(PublicBusinessStub.updated_at.desc())
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_stub(db: AsyncSession, org_id: uuid.UUID, stub_id: uuid.UUID) -> PublicBusinessStub | None:
    result = await db.execute(
        select(PublicBusinessStub).where(
            PublicBusinessStub.id == stub_id,
            PublicBusinessStub.org_id == org_id,
        )
    )
    return result.scalar_one_or_none()


async def create_stub(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    display_name: str,
    company_name: str,
    title: str | None,
    responsibility_keywords: list[str],
    product_keywords: list[str],
    external_card_url: str,
    one_line_blurb: str | None = None,
    avatar_url: str | None = None,
) -> PublicBusinessStub:
    if not validate_external_url(external_card_url):
        raise HTTPException(status_code=400, detail="INVALID_EXTERNAL_URL")
    if avatar_url and not validate_external_url(avatar_url):
        raise HTTPException(status_code=400, detail="INVALID_AVATAR_URL")

    stub = PublicBusinessStub(
        org_id=org_id,
        display_name=display_name.strip(),
        company_name=company_name.strip(),
        title=title.strip() if title else None,
        responsibility_keywords=responsibility_keywords,
        product_keywords=product_keywords,
        external_card_url=external_card_url.strip(),
        one_line_blurb=one_line_blurb.strip() if one_line_blurb else None,
        avatar_url=avatar_url.strip() if avatar_url else None,
        status="draft",
        created_by_user_id=user_id,
    )
    db.add(stub)
    await db.commit()
    await db.refresh(stub)
    return stub


async def update_stub(
    db: AsyncSession,
    stub: PublicBusinessStub,
    *,
    display_name: str | None = None,
    company_name: str | None = None,
    title: str | None = None,
    responsibility_keywords: list[str] | None = None,
    product_keywords: list[str] | None = None,
    external_card_url: str | None = None,
    one_line_blurb: str | None = None,
    avatar_url: str | None = None,
) -> PublicBusinessStub:
    if display_name is not None:
        stub.display_name = display_name.strip()
    if company_name is not None:
        stub.company_name = company_name.strip()
    if title is not None:
        stub.title = title.strip() or None
    if responsibility_keywords is not None:
        stub.responsibility_keywords = responsibility_keywords
    if product_keywords is not None:
        stub.product_keywords = product_keywords
    if external_card_url is not None:
        if not validate_external_url(external_card_url):
            raise HTTPException(status_code=400, detail="INVALID_EXTERNAL_URL")
        stub.external_card_url = external_card_url.strip()
    if one_line_blurb is not None:
        stub.one_line_blurb = one_line_blurb.strip() or None
    if avatar_url is not None:
        cleaned = avatar_url.strip()
        if cleaned and not validate_external_url(cleaned):
            raise HTTPException(status_code=400, detail="INVALID_AVATAR_URL")
        stub.avatar_url = cleaned or None

    was_published = stub.status == "published"
    await db.commit()
    await db.refresh(stub)
    if was_published:
        enqueue_stub_index(stub.id)
    return stub


async def delete_stub(db: AsyncSession, stub: PublicBusinessStub) -> None:
    if stub.status != "draft":
        raise HTTPException(status_code=409, detail="STUB_NOT_DRAFT")
    await db.delete(stub)
    await db.commit()


async def publish_stub(db: AsyncSession, stub: PublicBusinessStub) -> PublicBusinessStub:
    now = datetime.now(UTC)
    stub.status = "published"
    stub.published_at = now
    stub.unpublished_at = None
    await db.commit()
    await db.refresh(stub)
    enqueue_stub_index(stub.id)
    return stub


async def unpublish_stub(db: AsyncSession, stub: PublicBusinessStub) -> PublicBusinessStub:
    stub.status = "unpublished"
    stub.unpublished_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(stub)
    enqueue_stub_unindex(stub.id)
    return stub


async def import_csv(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    file: UploadFile,
    *,
    auto_publish: bool = False,
) -> dict:
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="INVALID_CSV_ENCODING") from exc

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or set(CSV_HEADERS) - set(reader.fieldnames):
        raise HTTPException(status_code=400, detail="INVALID_CSV_HEADERS")

    imported = 0
    skipped = 0
    errors: list[dict] = []

    for row_num, row in enumerate(reader, start=2):
        url = (row.get("external_card_url") or "").strip()
        display_name = (row.get("display_name") or "").strip()
        company_name = (row.get("company_name") or "").strip()
        if not display_name or not company_name or not url:
            skipped += 1
            errors.append({"row": row_num, "reason": "MISSING_REQUIRED_FIELD"})
            continue
        if not validate_external_url(url):
            skipped += 1
            errors.append({"row": row_num, "reason": "INVALID_EXTERNAL_URL"})
            continue

        stub = PublicBusinessStub(
            org_id=org_id,
            display_name=display_name,
            company_name=company_name,
            title=(row.get("title") or "").strip() or None,
            responsibility_keywords=_parse_keyword_cell(row.get("responsibility_keywords")),
            product_keywords=_parse_keyword_cell(row.get("product_keywords")),
            external_card_url=url,
            status="draft",
            created_by_user_id=user_id,
        )
        db.add(stub)
        await db.flush()
        if auto_publish:
            stub.status = "published"
            stub.published_at = datetime.now(UTC)
            enqueue_stub_index(stub.id)
        imported += 1

    await db.commit()
    return {"imported": imported, "skipped": skipped, "errors": errors}


async def get_published_public_card(
    db: AsyncSession, stub_id: uuid.UUID
) -> tuple[PublicBusinessStub, Organization] | None:
    result = await db.execute(
        select(PublicBusinessStub, Organization)
        .join(Organization, Organization.id == PublicBusinessStub.org_id)
        .where(
            PublicBusinessStub.id == stub_id,
            PublicBusinessStub.status == "published",
        )
    )
    row = result.one_or_none()
    if row is None:
        return None
    return row[0], row[1]


async def ensure_org_membership(
    db: AsyncSession,
    user: User,
    slug: str,
    org_name: str | None = None,
) -> Organization:
    result = await db.execute(select(Organization).where(Organization.slug == slug))
    org = result.scalar_one_or_none()
    if org is None:
        org = Organization(name=org_name or slug.replace("-", " ").title(), slug=slug)
        db.add(org)
        await db.flush()

    member = await db.execute(
        select(OrgMember).where(OrgMember.org_id == org.id, OrgMember.user_id == user.id)
    )
    if member.scalar_one_or_none() is None:
        db.add(OrgMember(org_id=org.id, user_id=user.id, role="admin"))
        await db.flush()

    return org


async def seed_demo_stubs(db: AsyncSession, org: Organization, user_id: uuid.UUID) -> None:
    published = await db.scalar(
        select(func.count())
        .select_from(PublicBusinessStub)
        .where(PublicBusinessStub.org_id == org.id, PublicBusinessStub.status == "published")
    )
    if published and published >= 3:
        return

    demos = [
        {
            "display_name": "王小明",
            "company_name": "Acme Taiwan",
            "title": "業務經理",
            "responsibility_keywords": ["OEM", "通路"],
            "product_keywords": ["工業電腦", "嵌入式"],
            "external_card_url": "https://example.com/card/acme-wang",
            "one_line_blurb": "幫製造商找對的通路夥伴",
        },
        {
            "display_name": "李美華",
            "company_name": "Acme Taiwan",
            "title": "技術窗口",
            "responsibility_keywords": ["技術支援", "PoC"],
            "product_keywords": ["邊緣運算", "IoT"],
            "external_card_url": "https://example.com/card/acme-lee",
            "one_line_blurb": "邊緣運算 PoC 與技術對接",
        },
        {
            "display_name": "陳志遠",
            "company_name": "Acme Taiwan",
            "title": "產品經理",
            "responsibility_keywords": ["產品規劃"],
            "product_keywords": ["自動化", "工控"],
            "external_card_url": "https://example.com/card/acme-chen",
            "one_line_blurb": "工控自動化產品規劃",
        },
    ]
    for item in demos:
        stub = PublicBusinessStub(
            org_id=org.id,
            created_by_user_id=user_id,
            status="published",
            published_at=datetime.now(UTC),
            **item,
        )
        db.add(stub)
        await db.flush()
        enqueue_stub_index(stub.id)
    await db.flush()

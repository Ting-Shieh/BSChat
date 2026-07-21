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


async def _require_org_member(
    db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    row = await db.execute(
        select(OrgMember).where(OrgMember.org_id == org_id, OrgMember.user_id == user_id)
    )
    if row.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="OWNER_NOT_ORG_MEMBER")


async def get_stub_for_owner(
    db: AsyncSession, org_id: uuid.UUID, owner_user_id: uuid.UUID
) -> PublicBusinessStub | None:
    result = await db.execute(
        select(PublicBusinessStub).where(
            PublicBusinessStub.org_id == org_id,
            PublicBusinessStub.owner_user_id == owner_user_id,
        )
    )
    return result.scalar_one_or_none()


async def ensure_member_public_identity(
    db: AsyncSession,
    *,
    org: Organization,
    user: User,
    created_by_user_id: uuid.UUID | None = None,
) -> PublicBusinessStub:
    """Enterprise default: identity exists, want AI on, pending until external URL set."""
    existing = await get_stub_for_owner(db, org.id, user.id)
    if existing is not None:
        return existing

    stub = PublicBusinessStub(
        org_id=org.id,
        display_name=(user.display_name or user.email).strip(),
        company_name=org.name,
        title=None,
        responsibility_keywords=[],
        product_keywords=[],
        external_card_url=None,
        status="draft",
        want_ai_recommend=True,
        created_by_user_id=created_by_user_id or user.id,
        owner_user_id=user.id,
    )
    db.add(stub)
    await db.flush()
    return stub


def stub_ai_state(stub: PublicBusinessStub | None) -> str:
    if stub is None:
        return "none"
    if stub.status == "published":
        return "on"
    if stub.want_ai_recommend and not (stub.external_card_url or "").strip():
        return "pending_url"
    return "off"


async def list_my_public_identities(db: AsyncSession, user: User) -> list[dict]:
    result = await db.execute(
        select(Organization, OrgMember, PublicBusinessStub)
        .join(OrgMember, OrgMember.org_id == Organization.id)
        .outerjoin(
            PublicBusinessStub,
            (PublicBusinessStub.org_id == Organization.id)
            & (PublicBusinessStub.owner_user_id == user.id),
        )
        .where(OrgMember.user_id == user.id, Organization.is_enterprise.is_(True))
        .order_by(Organization.name)
    )
    items: list[dict] = []
    for org, _member, stub in result.all():
        items.append(
            {
                "org_id": org.id,
                "org_name": org.name,
                "stub_id": stub.id if stub else None,
                "display_name": stub.display_name if stub else (user.display_name or user.email),
                "title": stub.title if stub else None,
                "external_card_url": stub.external_card_url if stub else None,
                "status": stub.status if stub else None,
                "want_ai_recommend": bool(stub.want_ai_recommend) if stub else True,
                "ai_state": stub_ai_state(stub),
            }
        )
    return items


async def update_my_public_identity(
    db: AsyncSession,
    user: User,
    org_id: uuid.UUID,
    *,
    external_card_url: str,
    title: str | None = None,
    display_name: str | None = None,
) -> PublicBusinessStub:
    org_result = await db.execute(
        select(Organization, OrgMember)
        .join(OrgMember, OrgMember.org_id == Organization.id)
        .where(
            Organization.id == org_id,
            Organization.is_enterprise.is_(True),
            OrgMember.user_id == user.id,
        )
    )
    row = org_result.one_or_none()
    if row is None:
        raise HTTPException(status_code=403, detail="NOT_ORG_MEMBER")
    org, _member = row

    stub = await ensure_member_public_identity(db, org=org, user=user, created_by_user_id=user.id)
    return await update_stub(
        db,
        stub,
        display_name=display_name,
        title=title,
        external_card_url=external_card_url,
        want_ai_recommend=True,
        auto_publish_if_ready=True,
    )


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
    external_card_url: str | None = None,
    one_line_blurb: str | None = None,
    avatar_url: str | None = None,
    publish: bool = True,
    owner_user_id: uuid.UUID | None = None,
    want_ai_recommend: bool = True,
    commit: bool = True,
) -> PublicBusinessStub:
    url = (external_card_url or "").strip() or None
    if url and not validate_external_url(url):
        raise HTTPException(status_code=400, detail="INVALID_EXTERNAL_URL")
    if avatar_url and not validate_external_url(avatar_url):
        raise HTTPException(status_code=400, detail="INVALID_AVATAR_URL")

    if publish:
        if owner_user_id is None:
            raise HTTPException(status_code=400, detail="OWNER_REQUIRED_FOR_PUBLISH")
        if not url:
            raise HTTPException(status_code=400, detail="EXTERNAL_URL_REQUIRED_FOR_PUBLISH")

    if owner_user_id is not None:
        await _require_org_member(db, org_id, owner_user_id)
        existing = await get_stub_for_owner(db, org_id, owner_user_id)
        if existing is not None:
            raise HTTPException(status_code=409, detail="OWNER_ALREADY_HAS_IDENTITY")

    now = datetime.now(UTC) if publish else None
    stub = PublicBusinessStub(
        org_id=org_id,
        display_name=display_name.strip(),
        company_name=company_name.strip(),
        title=title.strip() if title else None,
        responsibility_keywords=responsibility_keywords,
        product_keywords=product_keywords,
        external_card_url=url,
        one_line_blurb=one_line_blurb.strip() if one_line_blurb else None,
        avatar_url=avatar_url.strip() if avatar_url else None,
        status="published" if publish else "draft",
        published_at=now,
        want_ai_recommend=want_ai_recommend if not publish else True,
        created_by_user_id=user_id,
        owner_user_id=owner_user_id,
    )
    db.add(stub)
    if commit:
        await db.commit()
        await db.refresh(stub)
        if publish:
            enqueue_stub_index(stub.id)
    else:
        await db.flush()
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
    owner_user_id: uuid.UUID | None = None,
    want_ai_recommend: bool | None = None,
    auto_publish_if_ready: bool = True,
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
        cleaned_url = external_card_url.strip()
        if cleaned_url and not validate_external_url(cleaned_url):
            raise HTTPException(status_code=400, detail="INVALID_EXTERNAL_URL")
        stub.external_card_url = cleaned_url or None
    if one_line_blurb is not None:
        stub.one_line_blurb = one_line_blurb.strip() or None
    if avatar_url is not None:
        cleaned = avatar_url.strip()
        if cleaned and not validate_external_url(cleaned):
            raise HTTPException(status_code=400, detail="INVALID_AVATAR_URL")
        stub.avatar_url = cleaned or None
    if owner_user_id is not None:
        await _require_org_member(db, stub.org_id, owner_user_id)
        conflict = await get_stub_for_owner(db, stub.org_id, owner_user_id)
        if conflict is not None and conflict.id != stub.id:
            raise HTTPException(status_code=409, detail="OWNER_ALREADY_HAS_IDENTITY")
        stub.owner_user_id = owner_user_id
    if want_ai_recommend is not None:
        stub.want_ai_recommend = want_ai_recommend

    # Enterprise default: once URL exists and want AI, go live (unless explicitly unpublished off).
    if (
        auto_publish_if_ready
        and stub.want_ai_recommend
        and stub.owner_user_id
        and stub.external_card_url
        and stub.status in ("draft", "unpublished")
    ):
        # "unpublished" means admin turned off — only republish if want_ai_recommend flipped to True
        # via this update. If already unpublished and only URL changed, stay off unless want set True.
        if stub.status == "draft" or want_ai_recommend is True:
            stub.status = "published"
            stub.published_at = datetime.now(UTC)
            stub.unpublished_at = None

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
    if stub.owner_user_id is None:
        raise HTTPException(status_code=400, detail="OWNER_REQUIRED_FOR_PUBLISH")
    if not stub.external_card_url or not validate_external_url(stub.external_card_url):
        raise HTTPException(status_code=400, detail="EXTERNAL_URL_REQUIRED_FOR_PUBLISH")
    now = datetime.now(UTC)
    stub.status = "published"
    stub.published_at = now
    stub.unpublished_at = None
    stub.want_ai_recommend = True
    await db.commit()
    await db.refresh(stub)
    enqueue_stub_index(stub.id)
    return stub


async def unpublish_stub(db: AsyncSession, stub: PublicBusinessStub) -> PublicBusinessStub:
    stub.status = "unpublished"
    stub.unpublished_at = datetime.now(UTC)
    stub.want_ai_recommend = False
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
            want_ai_recommend=True,
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

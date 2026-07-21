import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.db import get_db
from app.modules.m11_public_directory.deps import OrgAdmin
from app.modules.m11_public_directory.service import (
    create_stub,
    delete_stub,
    get_org_summary,
    get_stub,
    import_csv,
    list_stubs,
    list_user_org_memberships,
    publish_stub,
    unpublish_stub,
    update_stub,
)
from app.schemas.org import (
    CsvImportResponse,
    OrgListResponse,
    OrgSummary,
    PublishResponse,
    StubCreateRequest,
    StubListResponse,
    StubResponse,
    StubUpdateRequest,
)

router = APIRouter(prefix="/orgs", tags=["orgs"])


def _to_stub_response(stub) -> StubResponse:
    return StubResponse(
        id=stub.id,
        org_id=stub.org_id,
        display_name=stub.display_name,
        company_name=stub.company_name,
        title=stub.title,
        responsibility_keywords=list(stub.responsibility_keywords or []),
        product_keywords=list(stub.product_keywords or []),
        external_card_url=stub.external_card_url,
        one_line_blurb=stub.one_line_blurb,
        avatar_url=stub.avatar_url,
        status=stub.status,
        want_ai_recommend=bool(getattr(stub, "want_ai_recommend", True)),
        published_at=stub.published_at,
        unpublished_at=stub.unpublished_at,
        created_at=stub.created_at,
        updated_at=stub.updated_at,
        share_path=f"/card/{stub.id}" if stub.status == "published" else None,
        owner_user_id=stub.owner_user_id,
    )


@router.get("/mine", response_model=OrgListResponse)
async def get_my_orgs(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrgListResponse:
    memberships = await list_user_org_memberships(db, user.id)
    items: list[OrgSummary] = []
    for org, _role in memberships:
        summary = await get_org_summary(db, org.id)
        items.append(
            OrgSummary(
                id=org.id,
                name=org.name,
                slug=org.slug,
                published_stub_count=summary["published_stub_count"],
            )
        )
    return OrgListResponse(items=items)


@router.get("/{org_id}", response_model=OrgSummary)
async def get_org(
    org: OrgAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrgSummary:
    summary = await get_org_summary(db, org.id)
    return OrgSummary(
        id=org.id,
        name=org.name,
        slug=org.slug,
        published_stub_count=summary["published_stub_count"],
    )


@router.get("/{org_id}/stubs", response_model=StubListResponse)
async def get_stubs(
    org: OrgAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = Query(default=None),
) -> StubListResponse:
    stubs = await list_stubs(db, org.id, status=status)
    return StubListResponse(items=[_to_stub_response(s) for s in stubs])


@router.post("/{org_id}/stubs", response_model=StubResponse, status_code=201)
async def post_stub(
    org: OrgAdmin,
    body: StubCreateRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StubResponse:
    stub = await create_stub(
        db,
        org.id,
        user.id,
        display_name=body.display_name,
        company_name=body.company_name,
        title=body.title,
        responsibility_keywords=body.responsibility_keywords,
        product_keywords=body.product_keywords,
        external_card_url=body.external_card_url,
        one_line_blurb=body.one_line_blurb,
        avatar_url=body.avatar_url,
        publish=body.allow_ai_recommend,
        owner_user_id=body.owner_user_id,
    )
    return _to_stub_response(stub)


@router.get("/{org_id}/stubs/{stub_id}", response_model=StubResponse)
async def get_stub_detail(
    org: OrgAdmin,
    stub_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StubResponse:
    stub = await get_stub(db, org.id, stub_id)
    if stub is None:
        raise HTTPException(status_code=404, detail="STUB_NOT_FOUND")
    return _to_stub_response(stub)


@router.patch("/{org_id}/stubs/{stub_id}", response_model=StubResponse)
async def patch_stub(
    org: OrgAdmin,
    stub_id: uuid.UUID,
    body: StubUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StubResponse:
    stub = await get_stub(db, org.id, stub_id)
    if stub is None:
        raise HTTPException(status_code=404, detail="STUB_NOT_FOUND")
    updated = await update_stub(
        db,
        stub,
        display_name=body.display_name,
        company_name=body.company_name,
        title=body.title,
        responsibility_keywords=body.responsibility_keywords,
        product_keywords=body.product_keywords,
        external_card_url=body.external_card_url,
        one_line_blurb=body.one_line_blurb,
        avatar_url=body.avatar_url,
        owner_user_id=body.owner_user_id,
        want_ai_recommend=body.want_ai_recommend,
    )
    return _to_stub_response(updated)


@router.delete("/{org_id}/stubs/{stub_id}", status_code=204)
async def remove_stub(
    org: OrgAdmin,
    stub_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    stub = await get_stub(db, org.id, stub_id)
    if stub is None:
        raise HTTPException(status_code=404, detail="STUB_NOT_FOUND")
    await delete_stub(db, stub)


@router.post("/{org_id}/stubs/{stub_id}/publish", response_model=PublishResponse)
async def post_publish(
    org: OrgAdmin,
    stub_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublishResponse:
    stub = await get_stub(db, org.id, stub_id)
    if stub is None:
        raise HTTPException(status_code=404, detail="STUB_NOT_FOUND")
    updated = await publish_stub(db, stub)
    return PublishResponse(status=updated.status)


@router.post("/{org_id}/stubs/{stub_id}/unpublish", response_model=StubResponse)
async def post_unpublish(
    org: OrgAdmin,
    stub_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StubResponse:
    stub = await get_stub(db, org.id, stub_id)
    if stub is None:
        raise HTTPException(status_code=404, detail="STUB_NOT_FOUND")
    updated = await unpublish_stub(db, stub)
    return _to_stub_response(updated)


@router.post("/{org_id}/stubs/import-csv", response_model=CsvImportResponse)
async def post_import_csv(
    org: OrgAdmin,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile,
    auto_publish: bool = Query(default=True),
) -> CsvImportResponse:
    result = await import_csv(
        db,
        org.id,
        user.id,
        file,
        auto_publish=auto_publish,
    )
    return CsvImportResponse(**result)

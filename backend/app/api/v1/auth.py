from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import create_access_token
from app.core.config import get_settings
from app.core.db import get_db
from app.core.entitlements import apply_plan_preset
from app.core.passwords import hash_password, verify_password
from app.models.user import User, UserEntitlement, Workspace
from app.modules.m11_public_directory.service import ensure_org_membership, seed_demo_stubs
from app.modules.team_invite import identity as idp
from app.modules.team_invite import service as invite_service
from app.schemas.auth import (
    DevLoginRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    PasswordLoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)

router = APIRouter()

_ALLOWED_PLAN_TIERS = frozenset({"free", "pro", "enterprise"})


class MagicLinkRequest(BaseModel):
    email: EmailStr
    invite_token: str | None = None


class MagicLinkResponse(BaseModel):
    sent: bool
    debug_link: str | None = Field(
        default=None,
        description="Only when ALLOW_DEV_LOGIN and email not sent — for local testing",
    )


async def _get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(
        select(User)
        .where(User.email == email.strip().lower())
        .options(selectinload(User.entitlement), selectinload(User.workspace))
    )
    return result.scalar_one_or_none()


async def _create_free_user(
    db: AsyncSession,
    *,
    email: str,
    display_name: str | None,
    password_hash: str | None,
) -> User:
    user = User(
        email=email.strip().lower(),
        display_name=display_name,
        password_hash=password_hash,
        password_changed_at=datetime.now(UTC) if password_hash else None,
    )
    db.add(user)
    await db.flush()
    db.add(Workspace(owner_user_id=user.id, name="Personal"))
    entitlement = UserEntitlement(user_id=user.id)
    apply_plan_preset(entitlement, "free")
    db.add(entitlement)
    await db.flush()
    return user


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    email = str(body.email).strip().lower()
    existing = await _get_user_by_email(db, email)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="EMAIL_ALREADY_REGISTERED")

    user = await _create_free_user(
        db,
        email=email,
        display_name=body.display_name,
        password_hash=hash_password(body.password),
    )
    if body.invite_token:
        await invite_service.accept_invite(db, user, body.invite_token)
    await db.commit()
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenResponse)
async def password_login(body: PasswordLoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    email = str(body.email).strip().lower()
    user = await _get_user_by_email(db, email)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_CREDENTIALS")
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/password/forgot", response_model=ForgotPasswordResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> ForgotPasswordResponse:
    settings = get_settings()
    email = str(body.email).strip().lower()
    user = await _get_user_by_email(db, email)
    if user is not None:
        _, reset_url = await idp.create_magic_login(
            db, email=email, invite_token=None, purpose="password_reset"
        )
        await db.commit()
        sent = await idp.send_password_reset_email(to_email=email, reset_url=reset_url)
        if not sent and not settings.allow_dev_login and not settings.resend_api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="EMAIL_NOT_CONFIGURED"
            )
    return ForgotPasswordResponse(sent=True)


@router.post("/password/reset", response_model=TokenResponse)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    email = await idp.consume_password_reset_token(db, body.token)
    user = await _get_user_by_email(db, email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="RESET_TOKEN_INVALID")
    user.password_hash = hash_password(body.new_password)
    user.password_changed_at = datetime.now(UTC)
    await db.commit()
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/dev-login", response_model=TokenResponse, summary="Local/dev login only")
async def dev_login(body: DevLoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    settings = get_settings()
    if not settings.allow_dev_login:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="DEV_LOGIN_DISABLED")

    plan_tier = (body.plan_tier or "free").lower()
    if plan_tier not in _ALLOWED_PLAN_TIERS:
        raise HTTPException(status_code=400, detail="UNKNOWN_PLAN_TIER")

    result = await db.execute(
        select(User).where(User.email == body.email).options(selectinload(User.entitlement))
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(email=body.email, display_name=body.display_name)
        db.add(user)
        await db.flush()
        workspace = Workspace(owner_user_id=user.id, name="Personal")
        entitlement = UserEntitlement(user_id=user.id)
        apply_plan_preset(entitlement, plan_tier)
        db.add(workspace)
        db.add(entitlement)
    else:
        if body.display_name:
            user.display_name = body.display_name
        entitlement = user.entitlement
        if entitlement is None:
            entitlement = UserEntitlement(user_id=user.id)
            db.add(entitlement)
        apply_plan_preset(entitlement, plan_tier)

    if body.seed_org:
        org = await ensure_org_membership(db, user, body.seed_org.strip().lower())
        if body.seed_org.strip().lower() == "acme-demo":
            await seed_demo_stubs(db, org, user.id)

    await db.commit()
    await db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/google/start")
async def google_start(
    invite_token: str | None = None,
    next: str = "/contacts",
) -> RedirectResponse:
    state = idp.encode_oauth_state(invite_token=invite_token, next_path=next)
    return RedirectResponse(idp.google_authorize_url(state), status_code=302)


@router.get("/google/callback")
async def google_callback(
    db: AsyncSession = Depends(get_db),
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"GOOGLE_OAUTH_{error}")
    if not code or not state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GOOGLE_OAUTH_MISSING_CODE")

    invite_token, next_path = idp.decode_oauth_state(state)
    identity = await idp.exchange_google_code(code)
    user = await idp.upsert_user_from_identity(db, identity)
    if invite_token:
        await invite_service.accept_invite(db, user, invite_token)
    await db.commit()
    token = create_access_token(user.id)
    return RedirectResponse(idp.frontend_auth_redirect(access_token=token, next_path=next_path), status_code=302)


@router.post("/magic-link", response_model=MagicLinkResponse)
async def request_magic_link(
    body: MagicLinkRequest,
    db: AsyncSession = Depends(get_db),
) -> MagicLinkResponse:
    settings = get_settings()
    _, verify_url = await idp.create_magic_login(
        db, email=str(body.email), invite_token=body.invite_token
    )
    await db.commit()
    sent = await idp.send_magic_email(to_email=str(body.email).lower(), verify_url=verify_url)
    debug_link = None if sent else (verify_url if settings.allow_dev_login else None)
    if not sent and not settings.allow_dev_login and not settings.resend_api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="EMAIL_NOT_CONFIGURED")
    return MagicLinkResponse(sent=sent, debug_link=debug_link)


@router.get("/magic-link/verify")
async def verify_magic_link(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    identity, invite_token = await idp.consume_magic_login(db, token)
    user = await idp.upsert_user_from_identity(db, identity)
    if invite_token:
        await invite_service.accept_invite(db, user, invite_token)
    await db.commit()
    jwt_token = create_access_token(user.id)
    return RedirectResponse(
        idp.frontend_auth_redirect(access_token=jwt_token, next_path="/contacts"),
        status_code=302,
    )


@router.get("/auth-mode")
async def auth_mode() -> dict[str, Any]:
    settings = get_settings()
    google_ready = bool(
        settings.google_oauth_client_id
        and settings.google_oauth_client_secret
        and settings.google_oauth_redirect_uri
    )
    email_ready = bool(settings.resend_api_key) or settings.allow_dev_login
    return {
        "password_auth_enabled": True,
        "google_enabled": google_ready,
        "password_reset_email_enabled": email_ready,
        "allow_dev_login": settings.allow_dev_login,
        # legacy keys (frontend may still read)
        "email_magic_link_enabled": False,
        "email_domain_allowlist": [
            d.strip() for d in (settings.auth_email_domain_allowlist or "").split(",") if d.strip()
        ],
        "server_time": datetime.now(UTC).isoformat(),
    }

"""Self-hosted identity: Google OAuth + email magic link (no Clerk)."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.entitlements import apply_plan_preset
from app.models.magic_login import MagicLoginToken
from app.models.user import User, UserEntitlement, Workspace


@dataclass(frozen=True)
class Identity:
    email: str
    display_name: str | None
    google_sub: str | None = None


async def upsert_user_from_identity(db: AsyncSession, identity: Identity) -> User:
    settings = get_settings()
    plan = (settings.dogfood_default_plan or "pro").lower()
    if plan not in {"free", "pro", "enterprise"}:
        plan = "pro"

    email = identity.email.strip().lower()
    _assert_email_allowed(email)

    user: User | None = None
    if identity.google_sub:
        result = await db.execute(
            select(User)
            .where(User.google_sub == identity.google_sub)
            .options(selectinload(User.entitlement), selectinload(User.workspace))
        )
        user = result.scalar_one_or_none()

    if user is None:
        result = await db.execute(
            select(User)
            .where(User.email == email)
            .options(selectinload(User.entitlement), selectinload(User.workspace))
        )
        user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=email,
            display_name=identity.display_name,
            google_sub=identity.google_sub,
        )
        db.add(user)
        await db.flush()
        db.add(Workspace(owner_user_id=user.id, name="Personal"))
        entitlement = UserEntitlement(user_id=user.id)
        apply_plan_preset(entitlement, plan)
        db.add(entitlement)
    else:
        user.email = email
        if identity.display_name:
            user.display_name = identity.display_name
        if identity.google_sub:
            user.google_sub = identity.google_sub
        if user.entitlement is None:
            entitlement = UserEntitlement(user_id=user.id)
            apply_plan_preset(entitlement, plan)
            db.add(entitlement)
        if user.workspace is None:
            db.add(Workspace(owner_user_id=user.id, name="Personal"))

    await db.flush()
    await db.refresh(user)
    return user


def _assert_email_allowed(email: str) -> None:
    settings = get_settings()
    raw = (settings.auth_email_domain_allowlist or "").strip()
    if not raw:
        return
    domains = {d.strip().lower().lstrip("@") for d in raw.split(",") if d.strip()}
    domain = email.split("@")[-1].lower() if "@" in email else ""
    if domain not in domains:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="EMAIL_DOMAIN_NOT_ALLOWED")


def encode_oauth_state(*, invite_token: str | None, next_path: str | None = None) -> str:
    settings = get_settings()
    payload = {
        "invite": invite_token,
        "next": next_path or "/contacts",
        "nonce": secrets.token_urlsafe(8),
        "exp": int((datetime.now(UTC) + timedelta(minutes=15)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_oauth_state(state: str) -> tuple[str | None, str]:
    settings = get_settings()
    try:
        payload = jwt.decode(state, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_OAUTH_STATE") from exc
    invite = payload.get("invite")
    next_path = payload.get("next") or "/contacts"
    if invite is not None and not isinstance(invite, str):
        invite = None
    if not isinstance(next_path, str) or not next_path.startswith("/"):
        next_path = "/contacts"
    return invite, next_path


def google_authorize_url(state: str) -> str:
    settings = get_settings()
    if not settings.google_oauth_client_id or not settings.google_oauth_redirect_uri:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="GOOGLE_OAUTH_NOT_CONFIGURED")
    params = {
        "client_id": settings.google_oauth_client_id,
        "redirect_uri": settings.google_oauth_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "include_granted_scopes": "true",
        "state": state,
        "prompt": "select_account",
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


async def exchange_google_code(code: str) -> Identity:
    settings = get_settings()
    if not (
        settings.google_oauth_client_id
        and settings.google_oauth_client_secret
        and settings.google_oauth_redirect_uri
    ):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="GOOGLE_OAUTH_NOT_CONFIGURED")

    async with httpx.AsyncClient(timeout=15.0) as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "redirect_uri": settings.google_oauth_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code >= 400:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="GOOGLE_TOKEN_EXCHANGE_FAILED")
        access_token = token_resp.json().get("access_token")
        if not access_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="GOOGLE_TOKEN_EXCHANGE_FAILED")

        info_resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if info_resp.status_code >= 400:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="GOOGLE_USERINFO_FAILED")
        data = info_resp.json()

    email = (data.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GOOGLE_EMAIL_REQUIRED")
    if data.get("email_verified") is False:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="GOOGLE_EMAIL_UNVERIFIED")
    sub = data.get("sub")
    name = (data.get("name") or "").strip() or None
    return Identity(email=email, display_name=name, google_sub=str(sub) if sub else None)


def hash_token(raw: str) -> str:
    import hashlib

    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def create_magic_login(
    db: AsyncSession,
    *,
    email: str,
    invite_token: str | None,
    purpose: str = "magic_login",
    expire_minutes: int | None = None,
) -> tuple[str, str]:
    """Returns (raw_token, verify_url). purpose: magic_login | password_reset."""
    settings = get_settings()
    email_norm = email.strip().lower()
    _assert_email_allowed(email_norm)
    raw = secrets.token_urlsafe(32)
    minutes = expire_minutes
    if minutes is None:
        minutes = 60 if purpose == "password_reset" else settings.magic_link_expire_minutes
    row = MagicLoginToken(
        token_hash=hash_token(raw),
        email=email_norm,
        invite_token=invite_token,
        purpose=purpose,
        expires_at=datetime.now(UTC) + timedelta(minutes=minutes),
    )
    db.add(row)
    await db.flush()
    if purpose == "password_reset":
        front = settings.frontend_base_url.rstrip("/")
        verify_url = f"{front}/reset-password?token={raw}"
    else:
        verify_url = (
            f"{settings.api_base_url.rstrip('/')}/api/v1/auth/magic-link/verify"
            f"?token={raw}"
        )
    return raw, verify_url


async def consume_magic_login(db: AsyncSession, raw_token: str) -> tuple[Identity, str | None]:
    result = await db.execute(
        select(MagicLoginToken).where(MagicLoginToken.token_hash == hash_token(raw_token.strip()))
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MAGIC_LINK_INVALID")
    if getattr(row, "purpose", "magic_login") != "magic_login":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MAGIC_LINK_INVALID")
    now = datetime.now(UTC)
    expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=UTC)
    if row.consumed_at is not None or expires < now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MAGIC_LINK_EXPIRED")
    row.consumed_at = now
    await db.flush()
    local = row.email.split("@")[0]
    return Identity(email=row.email, display_name=local, google_sub=None), row.invite_token


async def consume_password_reset_token(db: AsyncSession, raw_token: str) -> str:
    """Consume reset token; returns email. Raises RESET_TOKEN_INVALID."""
    result = await db.execute(
        select(MagicLoginToken).where(MagicLoginToken.token_hash == hash_token(raw_token.strip()))
    )
    row = result.scalar_one_or_none()
    if row is None or getattr(row, "purpose", "") != "password_reset":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="RESET_TOKEN_INVALID")
    now = datetime.now(UTC)
    expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=UTC)
    if row.consumed_at is not None or expires < now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="RESET_TOKEN_INVALID")
    row.consumed_at = now
    await db.flush()
    return row.email


async def send_magic_email(*, to_email: str, verify_url: str) -> bool:
    """Send via Resend when configured. Returns True if sent."""
    settings = get_settings()
    if not settings.resend_api_key:
        return False
    from_addr = settings.resend_from_email or "BSChat <onboarding@resend.dev>"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={
                "from": from_addr,
                "to": [to_email],
                "subject": "BSChat 登入連結",
                "html": (
                    f"<p>點擊下方連結登入 BSChat（{settings.magic_link_expire_minutes} 分鐘內有效）：</p>"
                    f'<p><a href="{verify_url}">{verify_url}</a></p>'
                ),
            },
        )
    if resp.status_code >= 400:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="EMAIL_SEND_FAILED")
    return True


async def send_password_reset_email(*, to_email: str, reset_url: str) -> bool:
    settings = get_settings()
    if not settings.resend_api_key:
        return False
    from_addr = settings.resend_from_email or "BSChat <onboarding@resend.dev>"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={
                "from": from_addr,
                "to": [to_email],
                "subject": "BSChat 重設密碼",
                "html": (
                    "<p>點擊下方連結重設 BSChat 密碼（1 小時內有效）：</p>"
                    f'<p><a href="{reset_url}">{reset_url}</a></p>'
                    "<p>若你沒有申請重設，請忽略此信。</p>"
                ),
            },
        )
    if resp.status_code >= 400:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="EMAIL_SEND_FAILED")
    return True


def frontend_auth_redirect(*, access_token: str, next_path: str = "/contacts") -> str:
    settings = get_settings()
    base = settings.frontend_base_url.rstrip("/")
    q = urlencode({"access_token": access_token, "next": next_path})
    return f"{base}/auth/callback?{q}"

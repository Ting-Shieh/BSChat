"""Password register / login / reset (M1 access)."""

from datetime import UTC, datetime, timedelta
import secrets

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import async_session_factory
from app.core.passwords import verify_password
from app.main import app
from app.models.magic_login import MagicLoginToken
from app.models.user import User
from app.modules.team_invite.identity import hash_token


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_register_login_and_duplicate():
    email = "pwd-reg-unique@example.com"
    async with _client() as client:
        r = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "secret123", "display_name": "Reg"},
        )
        assert r.status_code == 201, r.text
        assert "access_token" in r.json()

        r2 = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "secret123"},
        )
        assert r2.status_code == 409
        assert "EMAIL_ALREADY_REGISTERED" in r2.text

        bad = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "wrong-pass"},
        )
        assert bad.status_code == 401
        assert "INVALID_CREDENTIALS" in bad.text

        ok = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "secret123"},
        )
        assert ok.status_code == 200
        assert "access_token" in ok.json()

    async with async_session_factory() as db:
        from sqlalchemy.orm import selectinload

        row = (
            await db.execute(
                select(User).where(User.email == email).options(selectinload(User.entitlement))
            )
        ).scalar_one()
        assert row.password_hash
        assert row.password_hash != "secret123"
        assert verify_password("secret123", row.password_hash)
        assert row.entitlement.plan_tier == "free"


async def test_forgot_unknown_email_still_200():
    async with _client() as client:
        r = await client.post(
            "/api/v1/auth/password/forgot",
            json={"email": "nobody-exists-xyz@example.com"},
        )
        assert r.status_code == 200
        assert r.json()["sent"] is True


async def test_password_reset_flow():
    email = "pwd-reset@example.com"
    async with _client() as client:
        await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "oldpass12"},
        )

    raw = secrets.token_urlsafe(32)
    async with async_session_factory() as db:
        db.add(
            MagicLoginToken(
                token_hash=hash_token(raw),
                email=email,
                purpose="password_reset",
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
        await db.commit()

    async with _client() as client:
        reset = await client.post(
            "/api/v1/auth/password/reset",
            json={"token": raw, "new_password": "newpass99"},
        )
        assert reset.status_code == 200, reset.text
        assert "access_token" in reset.json()

        old = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "oldpass12"},
        )
        assert old.status_code == 401

        new = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "newpass99"},
        )
        assert new.status_code == 200


async def test_dev_login_and_plan_gated_when_disabled(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "allow_dev_login", False)

    async with _client() as client:
        r = await client.post(
            "/api/v1/auth/dev-login",
            json={"email": "gated@example.com", "plan_tier": "pro"},
        )
        assert r.status_code == 403

        reg = await client.post(
            "/api/v1/auth/register",
            json={"email": "gated-plan@example.com", "password": "secret123"},
        )
        assert reg.status_code == 201
        token = reg.json()["access_token"]
        plan = await client.post(
            "/api/v1/me/plan",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_tier": "pro"},
        )
        assert plan.status_code == 403

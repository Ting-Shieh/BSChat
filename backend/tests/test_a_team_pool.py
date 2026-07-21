"""Legacy org-wide pool retired — non-enterprise is personal-only."""

import uuid

import pytest

from app.core.db import async_session_factory
from app.core.team import get_team_user_ids
from app.models.organization import Organization, OrgMember
from app.models.user import User, Workspace


async def _mk_user(db) -> User:
    user = User(email=f"team-{uuid.uuid4()}@example.com", display_name="Teammate")
    db.add(user)
    await db.flush()
    db.add(Workspace(owner_user_id=user.id, name="Personal"))
    await db.flush()
    return user


@pytest.mark.asyncio
async def test_legacy_org_no_longer_shares_contacts():
    """DDR-v4-11: without enterprise sub-teams, org members do not share a pool."""
    async with async_session_factory() as db:
        org = Organization(name="Team Co", slug=f"team-{uuid.uuid4().hex[:8]}")
        db.add(org)
        await db.flush()

        alice = await _mk_user(db)
        bob = await _mk_user(db)
        carol = await _mk_user(db)
        db.add(OrgMember(org_id=org.id, user_id=alice.id, role="admin"))
        db.add(OrgMember(org_id=org.id, user_id=bob.id, role="member"))
        await db.commit()

        alice_team = set(await get_team_user_ids(db, alice.id))
        assert alice_team == {alice.id}
        assert bob.id not in alice_team

        carol_team = await get_team_user_ids(db, carol.id)
        assert carol_team == [carol.id]

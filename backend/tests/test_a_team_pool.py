"""A: team shared pool visibility engine — same-org members share, outsiders don't."""

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
async def test_team_scope_includes_org_members_excludes_outsiders():
    async with async_session_factory() as db:
        org = Organization(name="Team Co", slug=f"team-{uuid.uuid4().hex[:8]}")
        db.add(org)
        await db.flush()

        alice = await _mk_user(db)
        bob = await _mk_user(db)
        carol = await _mk_user(db)  # outsider, no org
        db.add(OrgMember(org_id=org.id, user_id=alice.id, role="admin"))
        db.add(OrgMember(org_id=org.id, user_id=bob.id, role="member"))
        await db.commit()

        alice_team = set(await get_team_user_ids(db, alice.id))
        assert alice.id in alice_team
        assert bob.id in alice_team, "teammate should be visible in the shared pool"
        assert carol.id not in alice_team, "outsider must not be in the team pool"

        # A user with no org falls back to just themselves (backward compatible).
        carol_team = await get_team_user_ids(db, carol.id)
        assert carol_team == [carol.id]

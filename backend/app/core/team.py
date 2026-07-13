"""Team-scope resolution for the shared contact pool (v1 dogfood).

L2 team pool: contacts stay owned by their capturer (contacts.user_id == who
captured), but visibility is expanded to every member of the same Organization
(via OrgMember). A user with no org falls back to just themselves — identical to
the previous per-user behaviour, so this is backward compatible.

This does NOT touch L3 (cross-company public directory / network scope), which
remains the paid tier.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import OrgMember


async def get_team_user_ids(db: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    """Return every user_id whose contacts this user may see (self + org teammates)."""
    org_ids = (
        await db.execute(select(OrgMember.org_id).where(OrgMember.user_id == user_id))
    ).scalars().all()
    if not org_ids:
        return [user_id]
    member_ids = (
        await db.execute(select(OrgMember.user_id).where(OrgMember.org_id.in_(org_ids)))
    ).scalars().all()
    ids = set(member_ids)
    ids.add(user_id)
    return list(ids)

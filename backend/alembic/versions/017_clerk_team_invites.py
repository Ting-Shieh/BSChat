"""Clerk user id + team invite links for dogfood auth."""

from typing import Sequence, Union

from alembic import op

revision: str = "017_clerk_team_invites"
down_revision: Union[str, None] = "016_contact_personal_note"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS clerk_user_id VARCHAR(128)"
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_users_clerk_user_id
        ON users (clerk_user_id)
        WHERE clerk_user_id IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS team_invites (
            id UUID PRIMARY KEY,
            org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            token_hash VARCHAR(64) NOT NULL UNIQUE,
            created_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            expires_at TIMESTAMPTZ NOT NULL,
            max_uses INTEGER NOT NULL DEFAULT 50,
            use_count INTEGER NOT NULL DEFAULT 0,
            revoked_at TIMESTAMPTZ NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_team_invites_org_id ON team_invites (org_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS team_invites")
    op.execute("DROP INDEX IF EXISTS ix_users_clerk_user_id")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS clerk_user_id")

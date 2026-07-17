"""Rename clerk_user_id → google_sub; add magic_login_tokens."""

from typing import Sequence, Union

from alembic import op

revision: str = "018_self_hosted_auth"
down_revision: Union[str, None] = "017_clerk_team_invites"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_clerk_user_id")
    op.execute(
        """
        DO $$ BEGIN
          IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='users' AND column_name='clerk_user_id'
          ) AND NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='users' AND column_name='google_sub'
          ) THEN
            ALTER TABLE users RENAME COLUMN clerk_user_id TO google_sub;
          END IF;
        END $$;
        """
    )
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS google_sub VARCHAR(128)"
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_users_google_sub
        ON users (google_sub)
        WHERE google_sub IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS magic_login_tokens (
            id UUID PRIMARY KEY,
            token_hash VARCHAR(64) NOT NULL UNIQUE,
            email VARCHAR(255) NOT NULL,
            invite_token VARCHAR(128) NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            consumed_at TIMESTAMPTZ NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_magic_login_tokens_email ON magic_login_tokens (email)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS magic_login_tokens")
    op.execute("DROP INDEX IF EXISTS ix_users_google_sub")
    op.execute(
        """
        DO $$ BEGIN
          IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='users' AND column_name='google_sub'
          ) THEN
            ALTER TABLE users RENAME COLUMN google_sub TO clerk_user_id;
          END IF;
        END $$;
        """
    )

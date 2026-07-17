"""021 — password auth fields + magic token purpose."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "021_password_auth"
down_revision: Union[str, None] = "020_ecard_blurb_avatar"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "magic_login_tokens",
        sa.Column("purpose", sa.String(length=32), nullable=False, server_default="magic_login"),
    )


def downgrade() -> None:
    op.drop_column("magic_login_tokens", "purpose")
    op.drop_column("users", "password_changed_at")
    op.drop_column("users", "password_hash")

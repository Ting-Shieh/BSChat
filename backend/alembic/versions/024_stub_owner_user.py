"""024 — public_business_stubs.owner_user_id (identity ↔ account)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "024_stub_owner_user"
down_revision: Union[str, None] = "023_sub_teams"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "public_business_stubs",
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_public_business_stubs_owner_user_id",
        "public_business_stubs",
        "users",
        ["owner_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_public_business_stubs_owner_user_id",
        "public_business_stubs",
        ["owner_user_id"],
    )
    op.create_index(
        "uq_stubs_org_owner",
        "public_business_stubs",
        ["org_id", "owner_user_id"],
        unique=True,
        postgresql_where=sa.text("owner_user_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_stubs_org_owner", table_name="public_business_stubs")
    op.drop_index("ix_public_business_stubs_owner_user_id", table_name="public_business_stubs")
    op.drop_constraint("fk_public_business_stubs_owner_user_id", "public_business_stubs", type_="foreignkey")
    op.drop_column("public_business_stubs", "owner_user_id")

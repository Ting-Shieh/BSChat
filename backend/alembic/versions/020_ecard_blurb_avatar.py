"""Add e-card optional blurb and avatar_url on public_business_stubs."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "020_ecard_blurb_avatar"
down_revision: Union[str, None] = "019_public_recommend_trial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("public_business_stubs", sa.Column("one_line_blurb", sa.Text(), nullable=True))
    op.add_column("public_business_stubs", sa.Column("avatar_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("public_business_stubs", "avatar_url")
    op.drop_column("public_business_stubs", "one_line_blurb")

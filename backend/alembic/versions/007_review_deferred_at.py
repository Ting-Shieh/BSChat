"""Add review_deferred_at to raw_cards for A2 skip queue."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_review_deferred"
down_revision: Union[str, None] = "006_search_quota_reset"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "raw_cards",
        sa.Column("review_deferred_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("raw_cards", "review_deferred_at")

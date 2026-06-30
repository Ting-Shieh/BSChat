"""M5 Stage 1b: user search_precision preference."""

from alembic import op
import sqlalchemy as sa

revision = "013_search_precision"
down_revision = "012_m5b_search_stub_results"
branch_labels = None
depends_on = None

VALID = ("strict", "balanced", "exploratory")


def upgrade() -> None:
    op.add_column(
        "user_entitlements",
        sa.Column("search_precision", sa.String(20), nullable=False, server_default="balanced"),
    )


def downgrade() -> None:
    op.drop_column("user_entitlements", "search_precision")

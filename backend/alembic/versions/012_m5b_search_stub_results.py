"""M5b: nullable contact_id + stub_id on search_results."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012_m5b_search_stub_results"
down_revision: Union[str, None] = "011_m11_public_directory"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("search_results", "contact_id", existing_type=postgresql.UUID(), nullable=True)
    op.add_column(
        "search_results",
        sa.Column("stub_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_search_results_stub_id",
        "search_results",
        "public_business_stubs",
        ["stub_id"],
        ["id"],
    )
    op.drop_constraint("uq_search_result_contact", "search_results", type_="unique")
    op.execute(
        """
        ALTER TABLE search_results
        ADD CONSTRAINT chk_search_result_target
        CHECK (contact_id IS NOT NULL OR stub_id IS NOT NULL)
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE search_results DROP CONSTRAINT IF EXISTS chk_search_result_target")
    op.drop_constraint("fk_search_results_stub_id", "search_results", type_="foreignkey")
    op.drop_column("search_results", "stub_id")
    op.alter_column("search_results", "contact_id", existing_type=postgresql.UUID(), nullable=False)
    op.create_unique_constraint("uq_search_result_contact", "search_results", ["query_id", "contact_id"])

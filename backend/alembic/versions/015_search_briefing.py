"""M5 C: opportunity briefing fields (opening line, collaboration note, dormant marker)."""

from typing import Sequence, Union

from alembic import op

revision: str = "015_search_briefing"
down_revision: Union[str, None] = "014_search_embeddings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE search_results ADD COLUMN IF NOT EXISTS opening_line TEXT")
    op.execute("ALTER TABLE search_results ADD COLUMN IF NOT EXISTS collaboration_note TEXT")
    op.execute("ALTER TABLE search_results ADD COLUMN IF NOT EXISTS dormant_months INTEGER")


def downgrade() -> None:
    op.execute("ALTER TABLE search_results DROP COLUMN IF EXISTS dormant_months")
    op.execute("ALTER TABLE search_results DROP COLUMN IF EXISTS collaboration_note")
    op.execute("ALTER TABLE search_results DROP COLUMN IF EXISTS opening_line")

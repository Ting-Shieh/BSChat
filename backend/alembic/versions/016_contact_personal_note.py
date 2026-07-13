"""B: human-entered personal note on contacts (preferences / relationship). AI never writes this."""

from typing import Sequence, Union

from alembic import op

revision: str = "016_contact_personal_note"
down_revision: Union[str, None] = "015_search_briefing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE contacts ADD COLUMN IF NOT EXISTS personal_note TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE contacts DROP COLUMN IF EXISTS personal_note")

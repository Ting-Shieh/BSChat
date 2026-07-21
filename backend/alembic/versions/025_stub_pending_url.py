"""025 — nullable external_card_url for pending AI identity; want_ai_recommend."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "025_stub_pending_url"
down_revision: Union[str, None] = "024_stub_owner_user"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "public_business_stubs",
        "external_card_url",
        existing_type=sa.Text(),
        nullable=True,
    )
    op.add_column(
        "public_business_stubs",
        sa.Column(
            "want_ai_recommend",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("public_business_stubs", "want_ai_recommend")
    op.execute(
        "UPDATE public_business_stubs SET external_card_url = 'https://example.com' "
        "WHERE external_card_url IS NULL"
    )
    op.alter_column(
        "public_business_stubs",
        "external_card_url",
        existing_type=sa.Text(),
        nullable=False,
    )

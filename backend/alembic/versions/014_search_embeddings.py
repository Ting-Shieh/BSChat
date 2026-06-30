"""M5 P1: pgvector embeddings on search index documents."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "014_search_embeddings"
down_revision: Union[str, None] = "013_search_precision"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIMS = 768


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        f"ALTER TABLE contact_search_documents "
        f"ADD COLUMN IF NOT EXISTS embedding vector({EMBEDDING_DIMS})"
    )
    op.execute(
        f"ALTER TABLE public_directory_documents "
        f"ADD COLUMN IF NOT EXISTS embedding vector({EMBEDDING_DIMS})"
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_csd_embedding
        ON contact_search_documents
        USING hnsw (embedding vector_cosine_ops)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pdd_embedding
        ON public_directory_documents
        USING hnsw (embedding vector_cosine_ops)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_pdd_embedding")
    op.execute("DROP INDEX IF EXISTS idx_csd_embedding")
    op.execute("ALTER TABLE public_directory_documents DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE contact_search_documents DROP COLUMN IF EXISTS embedding")

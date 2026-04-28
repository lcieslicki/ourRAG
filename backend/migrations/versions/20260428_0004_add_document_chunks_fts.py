"""add document_chunks table with full-text search for hybrid retrieval

Revision ID: 20260428_0004
Revises: 20260417_0003
Create Date: 2026-04-28 00:04:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260428_0004"
down_revision: str | None = "20260417_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("chunk_id", sa.String(length=255), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("document_version_id", sa.String(length=36), nullable=False),
        sa.Column("document_title", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("heading", sa.Text(), nullable=True),
        sa.Column("section_path_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("language", sa.String(length=16), nullable=False, server_default="pl"),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("chunking_strategy_name", sa.String(length=64), nullable=False, server_default="markdown_structure_v1"),
        sa.Column("chunking_strategy_version", sa.String(length=64), nullable=False, server_default="v1"),
        sa.Column("chunk_size_config", sa.Integer(), nullable=True),
        sa.Column("chunk_overlap_config", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chunk_id", name="uq_document_chunks_chunk_id"),
    )

    op.create_index("ix_document_chunks_workspace_id", "document_chunks", ["workspace_id"])
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_document_version_id", "document_chunks", ["document_version_id"])
    op.create_index("ix_document_chunks_is_active", "document_chunks", ["is_active"])
    op.create_index("ix_document_chunks_category", "document_chunks", ["category"])
    op.create_index("ix_document_chunks_language", "document_chunks", ["language"])

    # PostgreSQL full-text search vector column and index
    op.execute("""
        ALTER TABLE document_chunks
        ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
            setweight(to_tsvector('simple', coalesce(document_title, '')), 'A') ||
            setweight(to_tsvector('simple', coalesce(heading, '')), 'B') ||
            setweight(to_tsvector('simple', coalesce(section_path_text, '')), 'C') ||
            setweight(to_tsvector('simple', coalesce(chunk_text, '')), 'D')
        ) STORED
    """)
    op.create_index(
        "ix_document_chunks_search_vector",
        "document_chunks",
        ["search_vector"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_search_vector", table_name="document_chunks")
    op.drop_index("ix_document_chunks_language", table_name="document_chunks")
    op.drop_index("ix_document_chunks_category", table_name="document_chunks")
    op.drop_index("ix_document_chunks_is_active", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_version_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_workspace_id", table_name="document_chunks")
    op.drop_table("document_chunks")

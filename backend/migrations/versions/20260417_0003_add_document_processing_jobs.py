"""add document processing jobs table

Revision ID: 20260417_0003
Revises: 20260416_0002
Create Date: 2026-04-17 00:03:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260417_0003"
down_revision: str | None = "20260416_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_processing_jobs",
        sa.Column("document_version_id", sa.String(length=36), nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "attempts >= 0",
            name="ck_document_processing_jobs_attempts_non_negative",
        ),
        sa.CheckConstraint(
            "job_type IN ("
            "'parse_document', "
            "'chunk_document', "
            "'embed_document', "
            "'index_document', "
            "'reindex_document_version'"
            ")",
            name="ck_document_processing_jobs_job_type",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')",
            name="ck_document_processing_jobs_status",
        ),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_processing_jobs_status_created_at",
        "document_processing_jobs",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_document_processing_jobs_version_type",
        "document_processing_jobs",
        ["document_version_id", "job_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_document_processing_jobs_version_type", table_name="document_processing_jobs")
    op.drop_index("ix_document_processing_jobs_status_created_at", table_name="document_processing_jobs")
    op.drop_table("document_processing_jobs")

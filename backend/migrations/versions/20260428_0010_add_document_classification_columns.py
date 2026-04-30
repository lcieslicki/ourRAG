"""add document classification columns

Revision ID: 20260428_0010
Revises: 20260428_0005
Create Date: 2026-04-28 00:10:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260428_0010"
down_revision: str | None = "20260428_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "document_versions",
        sa.Column("inferred_doc_type", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "document_versions",
        sa.Column("inferred_doc_type_confidence", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("document_versions", "inferred_doc_type_confidence")
    op.drop_column("document_versions", "inferred_doc_type")

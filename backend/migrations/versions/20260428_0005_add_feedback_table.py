"""add feedback table for user feedback collection

Revision ID: 20260428_0005
Revises: 20260428_0004
Create Date: 2026-04-28 00:05:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260428_0005"
down_revision: str | None = "20260428_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feedback",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("message_id", sa.String(length=36), nullable=True),
        sa.Column("helpfulness", sa.String(length=32), nullable=True),
        sa.Column("source_quality", sa.String(length=32), nullable=True),
        sa.Column("answer_completeness", sa.String(length=32), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("response_mode", sa.String(length=64), nullable=True),
        sa.Column("cited_source_ids", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE", name="fk_feedback_workspace_id"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "conversation_id", "message_id", name="uq_feedback_workspace_conversation_message"),
    )

    op.create_index("ix_feedback_workspace_id", "feedback", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_feedback_workspace_id", table_name="feedback")
    op.drop_table("feedback")

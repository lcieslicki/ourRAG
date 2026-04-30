from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.common import IdMixin, TimestampMixin, utc_now
from app.infrastructure.db import Base


class Feedback(IdMixin, TimestampMixin, Base):
    __tablename__ = "feedback"
    __table_args__ = (
        UniqueConstraint("workspace_id", "conversation_id", "message_id", name="uq_feedback_workspace_conversation_message"),
    )

    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    helpfulness: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_quality: Mapped[str | None] = mapped_column(String(32), nullable=True)
    answer_completeness: Mapped[str | None] = mapped_column(String(32), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_mode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cited_source_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)

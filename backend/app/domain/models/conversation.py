from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.common import IdMixin, TimestampMixin, utc_now
from app.infrastructure.db import Base


class Conversation(IdMixin, TimestampMixin, Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("id", "workspace_id", name="uq_conversations_id_workspace"),
        CheckConstraint("status IN ('active', 'archived')", name="ck_conversations_status"),
    )

    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    selected_scope_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workspace = relationship("Workspace", back_populates="conversations")
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")
    summary = relationship("ConversationSummary", back_populates="conversation", uselist=False)


class Message(IdMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "id", name="uq_messages_conversation_id"),
        ForeignKeyConstraint(
            ["conversation_id", "workspace_id"],
            ["conversations.id", "conversations.workspace_id"],
            ondelete="CASCADE",
            name="fk_messages_conversation_workspace",
        ),
        CheckConstraint("role IN ('user', 'assistant', 'system')", name="ck_messages_role"),
        CheckConstraint("(role = 'assistant' AND user_id IS NULL) OR (role <> 'assistant')", name="ck_messages_assistant_user_null"),
    )

    conversation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")
    workspace = relationship("Workspace", overlaps="conversation,messages")
    user = relationship("User")
    summaries_as_last_message = relationship("ConversationSummary", back_populates="last_message")


class ConversationSummary(IdMixin, TimestampMixin, Base):
    __tablename__ = "conversation_summaries"
    __table_args__ = (
        UniqueConstraint("conversation_id", name="uq_conversation_summaries_conversation"),
        CheckConstraint("summary_version > 0", name="ck_conversation_summaries_summary_version_positive"),
    )

    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    summary_version: Mapped[int] = mapped_column(nullable=False, default=1)
    last_message_id: Mapped[str | None] = mapped_column(ForeignKey("messages.id", ondelete="RESTRICT"), nullable=True)

    conversation = relationship("Conversation", back_populates="summary")
    last_message = relationship("Message", back_populates="summaries_as_last_message")

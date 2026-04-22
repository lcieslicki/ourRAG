from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.common import IdMixin, TimestampMixin, utc_now
from app.infrastructure.db import Base


class Workspace(IdMixin, TimestampMixin, Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived', 'disabled')", name="ck_workspaces_status"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    default_language: Mapped[str] = mapped_column(String(16), nullable=False, default="pl")
    system_prompt_override: Mapped[str | None] = mapped_column(String, nullable=True)
    llm_model_override: Mapped[str | None] = mapped_column(String(255), nullable=True)
    embedding_model_override: Mapped[str | None] = mapped_column(String(255), nullable=True)
    settings_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    memberships = relationship("WorkspaceMembership", back_populates="workspace", passive_deletes=True)
    documents = relationship("Document", back_populates="workspace")
    conversations = relationship("Conversation", back_populates="workspace")


class WorkspaceMembership(IdMixin, Base):
    __tablename__ = "workspace_users"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_users_workspace_user"),
        CheckConstraint("role IN ('owner', 'admin', 'member', 'viewer')", name="ck_workspace_users_role"),
    )

    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    workspace = relationship("Workspace", back_populates="memberships")
    user = relationship("User", back_populates="memberships")

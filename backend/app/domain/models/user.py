from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.common import IdMixin, TimestampMixin
from app.infrastructure.db import Base


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'disabled', 'invited')", name="ck_users_status"),
    )

    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")

    memberships = relationship("WorkspaceMembership", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")
    documents_created = relationship("Document", back_populates="created_by_user")
    document_versions_created = relationship("DocumentVersion", back_populates="created_by_user")

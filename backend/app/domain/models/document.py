from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.common import IdMixin, TimestampMixin
from app.infrastructure.db import Base


class Document(IdMixin, TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("workspace_id", "slug", name="uq_documents_workspace_slug"),
        CheckConstraint("status IN ('active', 'archived', 'deleted')", name="ck_documents_status"),
    )

    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(120), nullable=False)
    tags_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workspace = relationship("Workspace", back_populates="documents")
    created_by_user = relationship("User", back_populates="documents_created")
    versions = relationship("DocumentVersion", back_populates="document")


class DocumentVersion(IdMixin, TimestampMixin, Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_document_versions_document_version_number"),
        CheckConstraint("version_number > 0", name="ck_document_versions_version_number_positive"),
        CheckConstraint("chunk_count >= 0", name="ck_document_versions_chunk_count_non_negative"),
        CheckConstraint(
            "processing_status IN ('pending', 'processing', 'ready', 'failed')",
            name="ck_document_versions_processing_status",
        ),
        CheckConstraint("NOT (is_active = true AND is_invalidated = true)", name="ck_document_versions_active_not_invalidated"),
        Index(
            "uq_document_versions_one_active_per_document",
            "document_id",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
    )

    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(32), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="pl")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_invalidated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    invalidated_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    parsed_text_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    embedding_model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    embedding_model_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chunking_strategy_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    document = relationship("Document", back_populates="versions")
    created_by_user = relationship("User", back_populates="document_versions_created")

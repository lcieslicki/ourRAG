"""SQLAlchemy model for the document_chunks table used by lexical retrieval."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db import Base


class DocumentChunk(Base):
    """Persistent searchable chunk record for lexical (FTS) retrieval."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        Index("ix_document_chunks_workspace_id", "workspace_id"),
        Index("ix_document_chunks_document_version_id", "document_version_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    chunk_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    document_version_id: Mapped[str] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False
    )
    document_title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    heading: Mapped[str | None] = mapped_column(Text, nullable=True)
    section_path_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="pl")
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    chunking_strategy_name: Mapped[str] = mapped_column(String(64), nullable=False, default="markdown_structure_v1")
    chunking_strategy_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")
    chunk_size_config: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_overlap_config: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    document_version = relationship("DocumentVersion", foreign_keys=[document_version_id])

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.common import IdMixin, TimestampMixin
from app.infrastructure.db import Base


class DocumentProcessingJob(IdMixin, TimestampMixin, Base):
    __tablename__ = "document_processing_jobs"
    __table_args__ = (
        CheckConstraint(
            "job_type IN ("
            "'parse_document', "
            "'chunk_document', "
            "'embed_document', "
            "'index_document', "
            "'reindex_document_version'"
            ")",
            name="ck_document_processing_jobs_job_type",
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')",
            name="ck_document_processing_jobs_status",
        ),
        CheckConstraint("attempts >= 0", name="ck_document_processing_jobs_attempts_non_negative"),
        Index("ix_document_processing_jobs_status_created_at", "status", "created_at"),
        Index("ix_document_processing_jobs_version_type", "document_version_id", "job_type"),
    )

    document_version_id: Mapped[str] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    document_version = relationship("DocumentVersion", back_populates="processing_jobs")

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.jobs import (
    ACTIVE_JOB_STATUSES,
    FAILED,
    INGESTION_JOB_FLOW,
    INGESTION_JOB_TYPES,
    QUEUED,
    RUNNING,
    SUCCEEDED,
    IngestionJobType,
)
from app.domain.models import DocumentProcessingJob, DocumentVersion
from app.domain.models.common import utc_now


class ProcessingJobNotFound(ValueError):
    pass


class UnsupportedProcessingJobType(ValueError):
    pass


class DocumentVersionForJobNotFound(ValueError):
    pass


class DocumentProcessingJobService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def enqueue(
        self,
        *,
        document_version_id: str,
        job_type: IngestionJobType,
        reuse_succeeded: bool = True,
    ) -> DocumentProcessingJob:
        self._validate_job_type(job_type)
        self._ensure_document_version_exists(document_version_id)

        existing = self._find_latest_job(document_version_id=document_version_id, job_type=job_type)
        reusable_statuses = (*ACTIVE_JOB_STATUSES, SUCCEEDED) if reuse_succeeded else ACTIVE_JOB_STATUSES
        if existing and existing.status in reusable_statuses:
            return existing

        job = DocumentProcessingJob(
            document_version_id=document_version_id,
            job_type=job_type,
            status=QUEUED,
            attempts=0,
        )
        self.session.add(job)
        self.session.flush()
        return job

    def enqueue_ingestion_flow(self, *, document_version_id: str) -> list[DocumentProcessingJob]:
        return [
            self.enqueue(document_version_id=document_version_id, job_type=job_type)
            for job_type in INGESTION_JOB_FLOW
        ]

    def mark_running(self, job: DocumentProcessingJob) -> DocumentProcessingJob:
        if job.status == SUCCEEDED:
            return job

        job.status = RUNNING
        job.attempts += 1
        job.error_message = None
        job.started_at = utc_now()
        job.finished_at = None
        self.session.flush()
        return job

    def mark_succeeded(self, job: DocumentProcessingJob) -> DocumentProcessingJob:
        job.status = SUCCEEDED
        job.error_message = None
        job.finished_at = utc_now()
        self.session.flush()
        return job

    def mark_failed(self, job: DocumentProcessingJob, *, error: Exception | str) -> DocumentProcessingJob:
        job.status = FAILED
        job.error_message = self._format_error(error)
        job.finished_at = utc_now()
        version = job.document_version
        if version is not None:
            version.processing_status = FAILED
        self.session.flush()
        return job

    def retry_failed(self, *, job_id: str) -> DocumentProcessingJob:
        job = self.get(job_id)
        if job.status != FAILED:
            return job

        job.status = QUEUED
        job.error_message = None
        job.started_at = None
        job.finished_at = None
        self.session.flush()
        return job

    def get(self, job_id: str) -> DocumentProcessingJob:
        job = self.session.get(DocumentProcessingJob, job_id)
        if job is None:
            raise ProcessingJobNotFound("Processing job not found.")
        return job

    def next_queued(self) -> DocumentProcessingJob | None:
        return self.session.scalar(
            select(DocumentProcessingJob)
            .where(DocumentProcessingJob.status == QUEUED)
            .order_by(DocumentProcessingJob.created_at, DocumentProcessingJob.id)
            .limit(1)
        )

    def _find_latest_job(self, *, document_version_id: str, job_type: IngestionJobType) -> DocumentProcessingJob | None:
        return self.session.scalar(
            select(DocumentProcessingJob)
            .where(
                DocumentProcessingJob.document_version_id == document_version_id,
                DocumentProcessingJob.job_type == job_type,
            )
            .order_by(DocumentProcessingJob.created_at.desc(), DocumentProcessingJob.id.desc())
            .limit(1)
        )

    def _ensure_document_version_exists(self, document_version_id: str) -> None:
        if self.session.get(DocumentVersion, document_version_id) is None:
            raise DocumentVersionForJobNotFound("Document version not found.")

    @staticmethod
    def _validate_job_type(job_type: str) -> None:
        if job_type not in INGESTION_JOB_TYPES:
            raise UnsupportedProcessingJobType(f"Unsupported processing job type: {job_type}")

    @staticmethod
    def _format_error(error: Exception | str) -> str:
        message = str(error)
        return message[:2000] if message else error.__class__.__name__

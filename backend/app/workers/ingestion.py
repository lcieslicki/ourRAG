from collections.abc import Callable

from sqlalchemy.orm import Session

from app.domain.jobs import (
    CHUNK_DOCUMENT,
    EMBED_DOCUMENT,
    INDEX_DOCUMENT,
    PARSE_DOCUMENT,
    REINDEX_DOCUMENT_VERSION,
)
from app.domain.models import DocumentProcessingJob, DocumentVersion
from app.domain.models.common import utc_now
from app.domain.services.processing_jobs import DocumentProcessingJobService

JobHandler = Callable[[DocumentProcessingJob], None]


class IngestionJobRunner:
    def __init__(self, session: Session, handlers: dict[str, JobHandler] | None = None) -> None:
        self.session = session
        self.jobs = DocumentProcessingJobService(session)
        self.handlers = handlers or self._default_handlers()

    def run_next(self) -> DocumentProcessingJob | None:
        job = self.jobs.next_queued()
        if job is None:
            return None
        return self.run(job.id)

    def run(self, job_id: str) -> DocumentProcessingJob:
        job = self.jobs.get(job_id)
        if job.status == "succeeded":
            return job

        self.jobs.mark_running(job)
        try:
            self.handlers[job.job_type](job)
        except Exception as exc:
            self.jobs.mark_failed(job, error=exc)
            return job

        self.jobs.mark_succeeded(job)
        return job

    def _default_handlers(self) -> dict[str, JobHandler]:
        return {
            PARSE_DOCUMENT: self._handle_parse_document,
            CHUNK_DOCUMENT: self._handle_chunk_document,
            EMBED_DOCUMENT: self._handle_embed_document,
            INDEX_DOCUMENT: self._handle_index_document,
            REINDEX_DOCUMENT_VERSION: self._handle_reindex_document_version,
        }

    def _handle_parse_document(self, job: DocumentProcessingJob) -> None:
        version = self._version_for(job)
        if version.processing_status == "pending":
            version.processing_status = "processing"
        self.jobs.enqueue(document_version_id=version.id, job_type=CHUNK_DOCUMENT)

    def _handle_chunk_document(self, job: DocumentProcessingJob) -> None:
        version = self._version_for(job)
        version.processing_status = "processing"
        self.jobs.enqueue(document_version_id=version.id, job_type=EMBED_DOCUMENT)

    def _handle_embed_document(self, job: DocumentProcessingJob) -> None:
        version = self._version_for(job)
        version.processing_status = "processing"
        self.jobs.enqueue(document_version_id=version.id, job_type=INDEX_DOCUMENT)

    def _handle_index_document(self, job: DocumentProcessingJob) -> None:
        version = self._version_for(job)
        version.processing_status = "ready"
        version.indexed_at = utc_now()

    def _handle_reindex_document_version(self, job: DocumentProcessingJob) -> None:
        version = self._version_for(job)
        version.processing_status = "pending"
        version.indexed_at = None
        self.jobs.enqueue(document_version_id=version.id, job_type=PARSE_DOCUMENT, reuse_succeeded=False)

    @staticmethod
    def _version_for(job: DocumentProcessingJob) -> DocumentVersion:
        version = job.document_version
        if version is None:
            raise ValueError("Document version not found for processing job.")
        if version.is_invalidated:
            raise ValueError("Invalidated document versions cannot be processed.")
        return version

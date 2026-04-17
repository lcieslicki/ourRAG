import pytest

from app.domain.models import DocumentProcessingJob
from app.domain.services.processing_jobs import (
    DocumentProcessingJobService,
    DocumentVersionForJobNotFound,
    UnsupportedProcessingJobType,
)
from tests.factories import create_document, create_document_version, create_user, create_workspace


def test_enqueue_creates_queued_job(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    document = create_document(db_session, workspace=workspace, created_by=user)
    version = create_document_version(db_session, document=document, created_by=user, version_number=1)

    job = DocumentProcessingJobService(db_session).enqueue(
        document_version_id=version.id,
        job_type="parse_document",
    )

    assert job.status == "queued"
    assert job.attempts == 0
    assert job.document_version_id == version.id


def test_enqueue_is_idempotent_for_existing_active_or_succeeded_job(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    document = create_document(db_session, workspace=workspace, created_by=user)
    version = create_document_version(db_session, document=document, created_by=user, version_number=1)
    service = DocumentProcessingJobService(db_session)

    first = service.enqueue(document_version_id=version.id, job_type="parse_document")
    second = service.enqueue(document_version_id=version.id, job_type="parse_document")
    service.mark_running(first)
    running = service.enqueue(document_version_id=version.id, job_type="parse_document")
    service.mark_succeeded(first)
    succeeded = service.enqueue(document_version_id=version.id, job_type="parse_document")

    assert second.id == first.id
    assert running.id == first.id
    assert succeeded.id == first.id
    assert db_session.query(DocumentProcessingJob).count() == 1


def test_enqueue_after_failed_job_creates_new_retryable_job(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    document = create_document(db_session, workspace=workspace, created_by=user)
    version = create_document_version(db_session, document=document, created_by=user, version_number=1)
    service = DocumentProcessingJobService(db_session)
    failed = service.enqueue(document_version_id=version.id, job_type="parse_document")
    service.mark_failed(failed, error="parser failed")

    retry = service.enqueue(document_version_id=version.id, job_type="parse_document")

    assert retry.id != failed.id
    assert retry.status == "queued"
    assert failed.status == "failed"
    assert version.processing_status == "failed"


def test_retry_failed_requeues_same_job_and_preserves_attempt_count(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    document = create_document(db_session, workspace=workspace, created_by=user)
    version = create_document_version(db_session, document=document, created_by=user, version_number=1)
    service = DocumentProcessingJobService(db_session)
    job = service.enqueue(document_version_id=version.id, job_type="parse_document")
    service.mark_running(job)
    service.mark_failed(job, error=RuntimeError("temporary failure"))

    retried = service.retry_failed(job_id=job.id)

    assert retried.id == job.id
    assert retried.status == "queued"
    assert retried.error_message is None
    assert retried.attempts == 1
    assert retried.finished_at is None


def test_enqueue_rejects_unknown_job_type(db_session) -> None:
    service = DocumentProcessingJobService(db_session)

    with pytest.raises(UnsupportedProcessingJobType):
        service.enqueue(document_version_id="missing", job_type="unknown")  # type: ignore[arg-type]


def test_enqueue_rejects_missing_document_version(db_session) -> None:
    service = DocumentProcessingJobService(db_session)

    with pytest.raises(DocumentVersionForJobNotFound):
        service.enqueue(document_version_id="missing", job_type="parse_document")

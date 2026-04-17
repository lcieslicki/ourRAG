from app.domain.models import DocumentProcessingJob
from app.domain.services.processing_jobs import DocumentProcessingJobService
from app.workers.ingestion import IngestionJobRunner
from tests.factories import create_document, create_document_version, create_user, create_workspace


def test_runner_advances_default_ingestion_flow_to_ready(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    document = create_document(db_session, workspace=workspace, created_by=user)
    version = create_document_version(db_session, document=document, created_by=user, version_number=1)
    version.processing_status = "pending"
    service = DocumentProcessingJobService(db_session)
    first = service.enqueue(document_version_id=version.id, job_type="parse_document")
    runner = IngestionJobRunner(db_session)

    assert runner.run(first.id).status == "succeeded"
    assert runner.run_next().job_type == "chunk_document"
    assert runner.run_next().job_type == "embed_document"
    assert runner.run_next().job_type == "index_document"

    assert version.processing_status == "ready"
    assert version.indexed_at is not None
    assert [job.job_type for job in db_session.query(DocumentProcessingJob).order_by(DocumentProcessingJob.created_at)] == [
        "parse_document",
        "chunk_document",
        "embed_document",
        "index_document",
    ]


def test_runner_failed_job_records_error_and_can_be_retried(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    document = create_document(db_session, workspace=workspace, created_by=user)
    version = create_document_version(db_session, document=document, created_by=user, version_number=1)
    service = DocumentProcessingJobService(db_session)
    job = service.enqueue(document_version_id=version.id, job_type="parse_document")
    runner = IngestionJobRunner(
        db_session,
        handlers={"parse_document": lambda _: (_ for _ in ()).throw(RuntimeError("boom"))},
    )

    failed = runner.run(job.id)

    assert failed.status == "failed"
    assert failed.attempts == 1
    assert failed.error_message == "boom"
    assert failed.finished_at is not None
    assert version.processing_status == "failed"

    retried = service.retry_failed(job_id=job.id)

    assert retried.status == "queued"
    assert retried.error_message is None


def test_runner_does_not_rerun_succeeded_job(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    document = create_document(db_session, workspace=workspace, created_by=user)
    version = create_document_version(db_session, document=document, created_by=user, version_number=1)
    service = DocumentProcessingJobService(db_session)
    job = service.enqueue(document_version_id=version.id, job_type="parse_document")
    service.mark_succeeded(job)
    calls = {"count": 0}

    def handler(_) -> None:
        calls["count"] += 1

    runner = IngestionJobRunner(db_session, handlers={"parse_document": handler})

    result = runner.run(job.id)

    assert result.status == "succeeded"
    assert calls["count"] == 0


def test_reindex_job_resets_version_and_enqueues_parse(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    document = create_document(db_session, workspace=workspace, created_by=user)
    version = create_document_version(db_session, document=document, created_by=user, version_number=1)
    service = DocumentProcessingJobService(db_session)
    job = service.enqueue(document_version_id=version.id, job_type="reindex_document_version")

    result = IngestionJobRunner(db_session).run(job.id)

    assert result.status == "succeeded"
    assert version.processing_status == "pending"
    assert version.indexed_at is None
    assert (
        db_session.query(DocumentProcessingJob)
        .filter_by(document_version_id=version.id, job_type="parse_document", status="queued")
        .count()
        == 1
    )


def test_reindex_job_enqueues_fresh_parse_after_previous_success(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    document = create_document(db_session, workspace=workspace, created_by=user)
    version = create_document_version(db_session, document=document, created_by=user, version_number=1)
    service = DocumentProcessingJobService(db_session)
    previous_parse = service.enqueue(document_version_id=version.id, job_type="parse_document")
    service.mark_succeeded(previous_parse)
    reindex = service.enqueue(document_version_id=version.id, job_type="reindex_document_version")

    IngestionJobRunner(db_session).run(reindex.id)

    parse_jobs = (
        db_session.query(DocumentProcessingJob)
        .filter_by(document_version_id=version.id, job_type="parse_document")
        .order_by(DocumentProcessingJob.created_at, DocumentProcessingJob.id)
        .all()
    )
    assert [job.status for job in parse_jobs] == ["succeeded", "queued"]

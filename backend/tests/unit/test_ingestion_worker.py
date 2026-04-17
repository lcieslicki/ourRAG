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


def test_runner_run_until_idle_processes_upload_pipeline(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    document = create_document(db_session, workspace=workspace, created_by=user)
    version = create_document_version(db_session, document=document, created_by=user, version_number=1)
    version.processing_status = "pending"
    service = DocumentProcessingJobService(db_session)
    service.enqueue_upload_pipeline(document_version_id=version.id)

    processed = IngestionJobRunner(db_session).run_until_idle()

    assert [job.job_type for job in processed] == [
        "parse_document",
        "chunk_document",
        "embed_document",
        "index_document",
    ]
    assert [job.status for job in processed] == ["succeeded", "succeeded", "succeeded", "succeeded"]
    assert version.processing_status == "ready"
    assert version.indexed_at is not None


def test_pipeline_records_status_transitions_before_ready(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    document = create_document(db_session, workspace=workspace, created_by=user)
    version = create_document_version(db_session, document=document, created_by=user, version_number=1)
    version.processing_status = "pending"
    service = DocumentProcessingJobService(db_session)
    first = service.enqueue_upload_pipeline(document_version_id=version.id)
    runner = IngestionJobRunner(db_session)

    parse_job = runner.run(first.id)
    chunk_job = runner.run_next()
    embed_job = runner.run_next()

    assert [parse_job.status, chunk_job.status, embed_job.status] == ["succeeded", "succeeded", "succeeded"]
    assert version.processing_status == "processing"
    assert version.indexed_at is None

    index_job = runner.run_next()

    assert index_job.status == "succeeded"
    assert version.processing_status == "ready"
    assert version.indexed_at is not None


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


def test_failed_embed_job_remains_failed_and_does_not_enqueue_index(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    document = create_document(db_session, workspace=workspace, created_by=user)
    version = create_document_version(db_session, document=document, created_by=user, version_number=1)
    version.processing_status = "pending"
    service = DocumentProcessingJobService(db_session)
    service.enqueue_upload_pipeline(document_version_id=version.id)
    runner = IngestionJobRunner(
        db_session,
        handlers={"embed_document": lambda _: (_ for _ in ()).throw(RuntimeError("embedding unavailable"))},
    )

    processed = runner.run_until_idle()

    assert [job.job_type for job in processed] == ["parse_document", "chunk_document", "embed_document"]
    assert [job.status for job in processed] == ["succeeded", "succeeded", "failed"]
    assert processed[-1].error_message == "embedding unavailable"
    assert version.processing_status == "failed"
    assert version.indexed_at is None
    assert db_session.query(DocumentProcessingJob).filter_by(document_version_id=version.id, job_type="index_document").count() == 0


def test_failed_embed_job_retry_can_finish_pipeline(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    document = create_document(db_session, workspace=workspace, created_by=user)
    version = create_document_version(db_session, document=document, created_by=user, version_number=1)
    version.processing_status = "pending"
    service = DocumentProcessingJobService(db_session)
    service.enqueue_upload_pipeline(document_version_id=version.id)
    failing_runner = IngestionJobRunner(
        db_session,
        handlers={"embed_document": lambda _: (_ for _ in ()).throw(RuntimeError("embedding unavailable"))},
    )
    failed_embed = failing_runner.run_until_idle()[-1]

    service.retry_failed(job_id=failed_embed.id)
    processed_after_retry = IngestionJobRunner(db_session).run_until_idle()

    assert failed_embed.attempts == 2
    assert failed_embed.status == "succeeded"
    assert [job.job_type for job in processed_after_retry] == ["embed_document", "index_document"]
    assert version.processing_status == "ready"
    assert version.indexed_at is not None


def test_retry_moves_version_back_to_processing_on_next_attempt(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    document = create_document(db_session, workspace=workspace, created_by=user)
    version = create_document_version(db_session, document=document, created_by=user, version_number=1)
    version.processing_status = "pending"
    service = DocumentProcessingJobService(db_session)
    job = service.enqueue_upload_pipeline(document_version_id=version.id)
    runner = IngestionJobRunner(
        db_session,
        handlers={"parse_document": lambda _: (_ for _ in ()).throw(RuntimeError("temporary parse failure"))},
    )
    runner.run(job.id)
    service.retry_failed(job_id=job.id)

    retried = IngestionJobRunner(db_session).run(job.id)

    assert retried.status == "succeeded"
    assert version.processing_status == "processing"


def test_downstream_job_cannot_mark_ready_when_previous_stage_failed(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    document = create_document(db_session, workspace=workspace, created_by=user)
    version = create_document_version(db_session, document=document, created_by=user, version_number=1)
    version.processing_status = "failed"
    service = DocumentProcessingJobService(db_session)
    chunk_job = service.enqueue(document_version_id=version.id, job_type="chunk_document")
    index_job = service.enqueue(document_version_id=version.id, job_type="index_document")
    runner = IngestionJobRunner(db_session)

    failed_chunk = runner.run(chunk_job.id)
    failed_index = runner.run(index_job.id)

    assert failed_chunk.status == "failed"
    assert "before successful parse_document" in failed_chunk.error_message
    assert failed_index.status == "failed"
    assert "before successful parse_document" in failed_index.error_message
    assert version.processing_status == "failed"
    assert version.indexed_at is None


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


def test_duplicate_upload_pipeline_enqueue_does_not_duplicate_jobs(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    document = create_document(db_session, workspace=workspace, created_by=user)
    version = create_document_version(db_session, document=document, created_by=user, version_number=1)
    version.processing_status = "pending"
    service = DocumentProcessingJobService(db_session)

    first = service.enqueue_upload_pipeline(document_version_id=version.id)
    second = service.enqueue_upload_pipeline(document_version_id=version.id)
    IngestionJobRunner(db_session).run_until_idle()

    jobs = db_session.query(DocumentProcessingJob).filter_by(document_version_id=version.id).all()
    assert second.id == first.id
    assert sorted(job.job_type for job in jobs) == [
        "chunk_document",
        "embed_document",
        "index_document",
        "parse_document",
    ]


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

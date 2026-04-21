from uuid import uuid4
import time

import httpx
import pytest

from app.core.config import get_settings
from app.domain.embeddings import EmbeddingMetadata, EmbeddingResult
from app.domain.services.processing_jobs import DocumentProcessingJobService
from app.infrastructure.storage.local import LocalFileStorage
from app.infrastructure.vector_index.qdrant import QdrantVectorIndex, VectorIndexQuery, VectorPoint
from app.workers.ingestion import IngestionJobRunner
from tests.factories import create_document, create_document_version, create_user, create_workspace


class DeterministicEmbeddingService:
    def __init__(self) -> None:
        self.embedded_chunk_texts: list[str] = []

    def embed_texts(self, inputs):
        return [
            EmbeddingResult(
                vector=[float(index + 1), 0.25],
                metadata=embedding_metadata(),
                input_metadata=item.metadata,
            )
            for index, item in enumerate(inputs)
        ]

    def embed_chunks(self, chunks):
        self.embedded_chunk_texts = [chunk.text for chunk in chunks]
        return [
            EmbeddingResult(
                vector=[float(index + 1), 0.25],
                metadata=embedding_metadata(),
                input_metadata={"chunk_index": chunk.chunk_index},
            )
            for index, chunk in enumerate(chunks)
        ]

    def embed_query(self, query: str):
        return EmbeddingResult(
            vector=[1.0, 0.25],
            metadata=embedding_metadata(),
            input_metadata={"input_type": "query"},
        )


@pytest.fixture()
def qdrant_index():
    settings = get_settings()
    base_url = f"http://{settings.qdrant.host}:{settings.qdrant.port}"
    collection = f"test_document_chunks_{uuid4().hex}"
    client = httpx.Client(timeout=2)

    try:
        client.get(f"{base_url}/collections").raise_for_status()
    except httpx.HTTPError as exc:
        client.close()
        pytest.skip(f"Qdrant is not available for integration tests: {exc}")

    index = QdrantVectorIndex(
        base_url=base_url,
        collection=collection,
        timeout_seconds=settings.qdrant.timeout,
    )

    try:
        yield index
    finally:
        client.delete(f"{base_url}/collections/{collection}")
        client.close()


def test_worker_generates_chunk_embeddings_and_indexes_into_qdrant(db_session, tmp_path, qdrant_index) -> None:
    workspace, document, version, storage = prepare_uploaded_markdown(db_session, tmp_path, is_active=True)
    embeddings = DeterministicEmbeddingService()
    DocumentProcessingJobService(db_session).enqueue_upload_pipeline(document_version_id=version.id)

    processed = IngestionJobRunner(
        db_session,
        storage=storage,
        embedding_service=embeddings,
        vector_index=qdrant_index,
    ).run_until_idle()

    assert [job.status for job in processed] == ["succeeded", "succeeded", "succeeded", "succeeded"]
    assert embeddings.embedded_chunk_texts
    assert version.processing_status == "ready"
    assert version.embedding_model_name == "deterministic-embed"
    assert version.embedding_model_version == "deterministic-embed:v1"
    assert version.indexed_at is not None

    results = wait_for_results(
        qdrant_index,
        VectorIndexQuery(workspace_id=workspace.id, vector=[1.0, 0.25], top_k=5),
        min_count=1,
    )

    payload = results[0].payload
    assert payload["workspace_id"] == workspace.id
    assert payload["document_id"] == document.id
    assert payload["document_version_id"] == version.id
    assert payload["category"] == document.category
    assert payload["language"] == version.language
    assert payload["is_active"] is True


def test_processed_version_is_indexed_as_active_for_standard_filter(db_session, tmp_path, qdrant_index) -> None:
    workspace, _, version, storage = prepare_uploaded_markdown(db_session, tmp_path, is_active=False)
    DocumentProcessingJobService(db_session).enqueue_upload_pipeline(document_version_id=version.id)

    IngestionJobRunner(
        db_session,
        storage=storage,
        embedding_service=DeterministicEmbeddingService(),
        vector_index=qdrant_index,
    ).run_until_idle()

    assert version.processing_status == "ready"
    assert version.is_active is True
    active_results = wait_for_results(
        qdrant_index,
        VectorIndexQuery(workspace_id=workspace.id, vector=[1.0, 0.25], top_k=5),
        min_count=1,
    )
    assert active_results[0].payload["is_active"] is True


def test_qdrant_delete_and_replace_document_version_vectors(qdrant_index) -> None:
    qdrant_index.ensure_collection(vector_size=2)
    first = vector_point(workspace_id="workspace-a", document_version_id="version-a", text="old text")
    replacement = vector_point(workspace_id="workspace-a", document_version_id="version-a", text="new text")

    qdrant_index.upsert_chunk_vectors([first])
    assert wait_for_results(
        qdrant_index,
        VectorIndexQuery(workspace_id="workspace-a", vector=[1.0, 0.0], top_k=5),
        min_count=1,
    )[0].payload["text"] == "old text"

    qdrant_index.upsert_chunk_vectors([replacement])
    replaced = wait_for_results(
        qdrant_index,
        VectorIndexQuery(workspace_id="workspace-a", vector=[1.0, 0.0], top_k=5),
        min_count=1,
        payload_text="new text",
    )
    assert len(replaced) == 1
    assert replaced[0].payload["text"] == "new text"

    qdrant_index.delete_document_version_vectors(workspace_id="workspace-a", document_version_id="version-a")
    wait_for_empty(qdrant_index, VectorIndexQuery(workspace_id="workspace-a", vector=[1.0, 0.0], top_k=5))


def test_workspace_filter_returns_only_matching_workspace(qdrant_index) -> None:
    qdrant_index.ensure_collection(vector_size=2)
    qdrant_index.upsert_chunk_vectors(
        [
            vector_point(workspace_id="workspace-a", document_version_id="version-a", text="workspace A"),
            vector_point(workspace_id="workspace-b", document_version_id="version-b", text="workspace B"),
        ]
    )

    results = wait_for_results(
        qdrant_index,
        VectorIndexQuery(workspace_id="workspace-a", vector=[1.0, 0.0], top_k=5),
        min_count=1,
    )

    assert {result.payload["workspace_id"] for result in results} == {"workspace-a"}
    assert {result.payload["text"] for result in results} == {"workspace A"}


def prepare_uploaded_markdown(db_session, tmp_path, *, is_active: bool):
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    document = create_document(db_session, workspace=workspace, created_by=user)
    version = create_document_version(
        db_session,
        document=document,
        created_by=user,
        version_number=1,
        is_active=is_active,
    )
    version.processing_status = "pending"
    storage = LocalFileStorage(tmp_path)
    version.storage_path = storage.original_file_path(
        workspace_id=workspace.id,
        document_id=document.id,
        version_id=version.id,
        file_name="policy.md",
    )
    storage.write_text(
        relative_path=version.storage_path,
        content="# Policy\n\nAlpha content for embeddings.\n\n## Details\n\nBeta content for indexing.\n",
    )
    return workspace, document, version, storage


def vector_point(*, workspace_id: str, document_version_id: str, text: str) -> VectorPoint:
    return VectorPoint(
        chunk_id=f"{document_version_id}:0",
        vector=[1.0, 0.0],
        workspace_id=workspace_id,
        document_id=f"document-{workspace_id}",
        document_version_id=document_version_id,
        chunk_index=0,
        text=text,
        title="Policy",
        category="HR",
        section_path=["Policy"],
        language="pl",
        is_active=True,
        embedding=embedding_metadata(),
    )


def embedding_metadata() -> EmbeddingMetadata:
    return EmbeddingMetadata(
        provider="deterministic",
        model_name="deterministic-embed",
        model_version="deterministic-embed:v1",
        dimensions=2,
    )


def wait_for_results(
    index: QdrantVectorIndex,
    query: VectorIndexQuery,
    *,
    min_count: int,
    payload_text: str | None = None,
):
    last_results = []
    for _ in range(20):
        last_results = index.query(query)
        if len(last_results) >= min_count and (
            payload_text is None or any(result.payload.get("text") == payload_text for result in last_results)
        ):
            return last_results
        time.sleep(0.05)

    return last_results


def wait_for_empty(index: QdrantVectorIndex, query: VectorIndexQuery) -> None:
    for _ in range(20):
        if index.query(query) == []:
            return
        time.sleep(0.05)

    assert index.query(query) == []

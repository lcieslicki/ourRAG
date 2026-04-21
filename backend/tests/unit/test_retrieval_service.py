import pytest

from app.core.config import get_settings
from app.domain.embeddings import EmbeddingMetadata, EmbeddingResult
from app.domain.errors import DocumentAccessDenied, WorkspaceAccessDenied
from app.domain.services.retrieval import RetrievalScope, RetrievalService
from app.infrastructure.vector_index import VectorIndexQuery, VectorIndexResult
from tests.factories import create_document, create_document_version, create_membership, create_user, create_workspace


class FakeEmbeddingService:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def embed_texts(self, inputs):
        return []

    def embed_chunks(self, chunks):
        return []

    def embed_query(self, query: str) -> EmbeddingResult:
        self.queries.append(query)
        return EmbeddingResult(
            vector=[0.1, 0.2],
            metadata=EmbeddingMetadata(
                provider="fake",
                model_name="fake-query-embed",
                model_version="fake-query-embed:v1",
                dimensions=2,
            ),
            input_metadata={"input_type": "query"},
        )


class FakeVectorIndex:
    def __init__(self, results: list[VectorIndexResult] | None = None) -> None:
        self.results = results or []
        self.queries: list[VectorIndexQuery] = []

    def query(self, query: VectorIndexQuery) -> list[VectorIndexResult]:
        self.queries.append(query)
        return self.results


def test_retrieval_validates_workspace_access(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    service = retrieval_service(db_session, vector_index=FakeVectorIndex())

    with pytest.raises(WorkspaceAccessDenied):
        service.retrieve(
            user_id=user.id,
            workspace_id=workspace.id,
            query="vacation policy",
        )


def test_retrieval_embeds_query_and_queries_qdrant_with_mandatory_filters(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=user, workspace=workspace, role="member")
    embeddings = FakeEmbeddingService()
    document, version = create_ready_active_version(db_session, workspace=workspace, user=user)
    vector_index = FakeVectorIndex(
        [
            vector_result(
                workspace_id=workspace.id,
                document_id=document.id,
                document_version_id=version.id,
                chunk_id="chunk-1",
            )
        ]
    )
    service = retrieval_service(db_session, embedding_service=embeddings, vector_index=vector_index)

    response = service.retrieve(
        user_id=user.id,
        workspace_id=workspace.id,
        query="  vacation policy  ",
    )

    assert embeddings.queries == ["vacation policy"]
    assert response.query == "vacation policy"
    assert len(response.chunks) == 1
    qdrant_query = vector_index.queries[0]
    assert qdrant_query.workspace_id == workspace.id
    assert qdrant_query.vector == [0.1, 0.2]
    assert qdrant_query.top_k == get_settings().retrieval.top_k
    assert qdrant_query.active_only is True


def test_retrieval_passes_optional_scope_filters(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=user, workspace=workspace, role="viewer")
    first_document = create_document(db_session, workspace=workspace, created_by=user, slug_prefix="doc-a")
    second_document = create_document(db_session, workspace=workspace, created_by=user, slug_prefix="doc-b")
    vector_index = FakeVectorIndex()
    service = retrieval_service(db_session, vector_index=vector_index)

    service.retrieve(
        user_id=user.id,
        workspace_id=workspace.id,
        query="policy",
        scope=RetrievalScope(
            category="HR",
            document_ids=(first_document.id, second_document.id),
            language="pl",
        ),
        top_k=7,
    )

    qdrant_query = vector_index.queries[0]
    assert qdrant_query.category == "HR"
    assert qdrant_query.document_ids == [first_document.id, second_document.id]
    assert qdrant_query.language == "pl"
    assert qdrant_query.top_k == 7
    assert qdrant_query.active_only is True


def test_retrieval_rejects_selected_documents_outside_workspace(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session, slug_prefix="workspace-a")
    other_workspace = create_workspace(db_session, slug_prefix="workspace-b")
    create_membership(db_session, user=user, workspace=workspace, role="member")
    other_document = create_document(db_session, workspace=other_workspace, created_by=user)
    vector_index = FakeVectorIndex()
    service = retrieval_service(db_session, vector_index=vector_index)

    with pytest.raises(DocumentAccessDenied):
        service.retrieve(
            user_id=user.id,
            workspace_id=workspace.id,
            query="policy",
            scope=RetrievalScope(document_ids=(other_document.id,)),
        )

    assert vector_index.queries == []


def test_retrieval_filters_payload_defensively_and_deduplicates_chunks(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=user, workspace=workspace, role="member")
    document, version = create_ready_active_version(db_session, workspace=workspace, user=user)
    vector_index = FakeVectorIndex(
        [
            vector_result(
                workspace_id=workspace.id,
                document_id=document.id,
                document_version_id=version.id,
                chunk_id="chunk-1",
                score=0.9,
            ),
            vector_result(
                workspace_id=workspace.id,
                document_id=document.id,
                document_version_id=version.id,
                chunk_id="chunk-1",
                score=0.8,
            ),
            vector_result(
                workspace_id=workspace.id,
                document_id=document.id,
                document_version_id=version.id,
                chunk_id="inactive",
                is_active=False,
            ),
            vector_result(workspace_id="other-workspace", chunk_id="other"),
            vector_result(
                workspace_id=workspace.id,
                document_id=document.id,
                document_version_id=version.id,
                chunk_id="chunk-2",
                score=0.7,
            ),
        ]
    )
    service = retrieval_service(db_session, vector_index=vector_index)

    response = service.retrieve(user_id=user.id, workspace_id=workspace.id, query="policy")

    assert [chunk.chunk_id for chunk in response.chunks] == ["chunk-1", "chunk-2"]
    assert all(chunk.is_active for chunk in response.chunks)
    assert all(chunk.payload["workspace_id"] == workspace.id for chunk in response.chunks)


def test_retrieval_limits_chunks_for_prompt_context(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=user, workspace=workspace, role="member")
    document, version = create_ready_active_version(db_session, workspace=workspace, user=user)
    results = [
        vector_result(
            workspace_id=workspace.id,
            document_id=document.id,
            document_version_id=version.id,
            chunk_id=f"chunk-{index}",
            score=1.0 - index / 100,
        )
        for index in range(get_settings().retrieval.max_context_chunks + 2)
    ]
    service = retrieval_service(db_session, vector_index=FakeVectorIndex(results))

    response = service.retrieve(user_id=user.id, workspace_id=workspace.id, query="policy")

    assert len(response.chunks) == get_settings().retrieval.max_context_chunks


def test_retrieval_rejects_empty_query(db_session) -> None:
    service = retrieval_service(db_session, vector_index=FakeVectorIndex())

    with pytest.raises(ValueError):
        service.retrieve(user_id="user", workspace_id="workspace", query="  ")


def retrieval_service(
    db_session,
    *,
    embedding_service: FakeEmbeddingService | None = None,
    vector_index: FakeVectorIndex,
) -> RetrievalService:
    return RetrievalService(
        session=db_session,
        embedding_service=embedding_service or FakeEmbeddingService(),
        vector_index=vector_index,
        settings=get_settings(),
    )


def vector_result(
    *,
    workspace_id: str,
    chunk_id: str,
    document_id: str = "document-1",
    document_version_id: str = "version-1",
    score: float = 0.9,
    is_active: bool = True,
) -> VectorIndexResult:
    return VectorIndexResult(
        id=chunk_id,
        score=score,
        payload={
            "workspace_id": workspace_id,
            "document_id": document_id,
            "document_version_id": document_version_id,
            "chunk_id": chunk_id,
            "text": f"text for {chunk_id}",
            "title": "Policy",
            "section_path": ["Policy"],
            "category": "HR",
            "language": "pl",
            "is_active": is_active,
        },
    )


def create_ready_active_version(db_session, *, workspace, user):
    document = create_document(db_session, workspace=workspace, created_by=user)
    version = create_document_version(db_session, document=document, created_by=user, version_number=1, is_active=True)
    version.processing_status = "ready"
    db_session.flush()
    return document, version

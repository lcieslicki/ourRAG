import json

import httpx

from app.domain.embeddings import EmbeddingMetadata
from app.infrastructure.vector_index.qdrant import (
    QdrantVectorIndex,
    VectorIndexQuery,
    VectorPoint,
    build_retrieval_filter,
)


def test_upsert_chunk_vectors_sends_expected_payload() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"result": {"operation_id": 1}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    index = QdrantVectorIndex(
        base_url="http://qdrant:6333",
        collection="document_chunks",
        timeout_seconds=10,
        client=client,
    )
    point = VectorPoint(
        chunk_id="version-1:0",
        vector=[0.1, 0.2],
        workspace_id="workspace-1",
        document_id="document-1",
        document_version_id="version-1",
        chunk_index=0,
        text="Chunk text",
        title="Policy",
        category="HR",
        section_path=["Policy"],
        language="pl",
        is_active=True,
        tags=["hr"],
        embedding=EmbeddingMetadata(
            provider="ollama",
            model_name="nomic-embed-text",
            model_version="ollama:nomic-embed-text",
            dimensions=2,
        ),
    )

    index.upsert_chunk_vectors([point])

    assert requests[0].method == "PUT"
    assert requests[0].url == "http://qdrant:6333/collections/document_chunks/points"
    payload = requests[0].read()
    assert b'"workspace_id":"workspace-1"' in payload
    assert b'"document_version_id":"version-1"' in payload
    assert b'"chunk_id":"version-1:0"' in payload
    assert b'"embedding_model_version":"ollama:nomic-embed-text"' in payload


def test_delete_document_version_vectors_filters_by_workspace_and_version() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"result": {"operation_id": 2}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    index = QdrantVectorIndex(
        base_url="http://qdrant:6333",
        collection="document_chunks",
        timeout_seconds=10,
        client=client,
    )

    index.delete_document_version_vectors(workspace_id="workspace-1", document_version_id="version-1")

    assert requests[0].method == "POST"
    assert requests[0].url == "http://qdrant:6333/collections/document_chunks/points/delete"
    assert requests[0].read() == (
        b'{"filter":{"must":[{"key":"workspace_id","match":{"value":"workspace-1"}},'
        b'{"key":"document_version_id","match":{"value":"version-1"}}]}}'
    )


def test_query_always_includes_workspace_and_active_filters() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "result": [
                    {
                        "id": "point-1",
                        "score": 0.91,
                        "payload": {"workspace_id": "workspace-1", "chunk_id": "chunk-1"},
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    index = QdrantVectorIndex(
        base_url="http://qdrant:6333",
        collection="document_chunks",
        timeout_seconds=10,
        client=client,
    )

    results = index.query(
        VectorIndexQuery(
            workspace_id="workspace-1",
            vector=[0.1, 0.2],
            top_k=5,
            category="HR",
            document_ids=["document-1", "document-2"],
            language="pl",
        )
    )

    assert results[0].score == 0.91
    payload = json.loads(requests[0].read())
    assert payload["filter"]["must"] == [
        {"key": "workspace_id", "match": {"value": "workspace-1"}},
        {"key": "is_active", "match": {"value": True}},
        {"key": "category", "match": {"value": "HR"}},
        {"key": "language", "match": {"value": "pl"}},
        {"key": "document_id", "match": {"any": ["document-1", "document-2"]}},
    ]


def test_build_retrieval_filter_has_mandatory_filters_only_by_default() -> None:
    query = VectorIndexQuery(workspace_id="workspace-1", vector=[0.1], top_k=3)

    assert build_retrieval_filter(query) == {
        "must": [
            {"key": "workspace_id", "match": {"value": "workspace-1"}},
            {"key": "is_active", "match": {"value": True}},
        ]
    }


def test_ensure_collection_uses_configured_collection_name() -> None:
    requests: list[httpx.Request] = []
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: requests.append(request) or httpx.Response(200, json={"result": True})
        )
    )
    index = QdrantVectorIndex(
        base_url="http://qdrant:6333",
        collection="document_chunks",
        timeout_seconds=10,
        client=client,
    )

    index.ensure_collection(vector_size=768)

    assert requests[0].method == "PUT"
    assert requests[0].url == "http://qdrant:6333/collections/document_chunks"
    assert requests[0].read() == b'{"vectors":{"size":768,"distance":"Cosine"}}'

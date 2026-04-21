import httpx
import pytest

from app.domain.chunking.markdown import DocumentChunk
from app.domain.embeddings import EmbeddingInput
from app.infrastructure.embeddings.ollama import (
    EmbeddingProviderError,
    OllamaEmbeddingService,
    parse_ollama_embedding_response,
)


def test_embed_query_calls_ollama_embed_endpoint() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2, 0.3]]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    service = OllamaEmbeddingService(
        base_url="http://ollama:11434",
        model_name="nomic-embed-text",
        timeout_seconds=30,
        client=client,
    )

    result = service.embed_query("What is the vacation policy?")

    assert result.vector == [0.1, 0.2, 0.3]
    assert result.input_metadata == {"input_type": "query"}
    assert result.metadata.provider == "ollama"
    assert result.metadata.model_name == "nomic-embed-text"
    assert result.metadata.model_version == "ollama:nomic-embed-text"
    assert result.metadata.dimensions == 3
    assert requests[0].url == "http://ollama:11434/api/embed"
    assert requests[0].read() == b'{"model":"nomic-embed-text","input":["What is the vacation policy?"]}'


def test_embed_query_falls_back_to_legacy_ollama_embeddings_endpoint_on_404() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url == "http://ollama:11434/api/embed":
            return httpx.Response(404)
        if request.url == "http://ollama:11434/api/embeddings":
            return httpx.Response(200, json={"embedding": [0.7, 0.8]})
        return httpx.Response(500)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    service = OllamaEmbeddingService(
        base_url="http://ollama:11434",
        model_name="nomic-embed-text",
        timeout_seconds=30,
        client=client,
    )

    result = service.embed_query("fallback please")

    assert result.vector == [0.7, 0.8]
    assert requests[0].url == "http://ollama:11434/api/embed"
    assert requests[1].url == "http://ollama:11434/api/embeddings"
    assert requests[1].read() == b'{"model":"nomic-embed-text","prompt":"fallback please"}'


def test_embed_chunks_preserves_chunk_metadata() -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"embeddings": [[1, 2]]})))
    service = OllamaEmbeddingService(
        base_url="http://ollama:11434",
        model_name="nomic-embed-text",
        timeout_seconds=30,
        client=client,
    )
    chunk = DocumentChunk(
        chunk_index=7,
        text="Policy text",
        heading="Vacation",
        section_path=("HR", "Vacation"),
        document_version_id="version-1",
        workspace_id="workspace-1",
        language="pl",
        chunking_strategy_version="markdown_semantic_v1",
    )

    result = service.embed_chunks([chunk])[0]

    assert result.vector == [1.0, 2.0]
    assert result.input_metadata == {
        "chunk_index": 7,
        "heading": "Vacation",
        "section_path": ["HR", "Vacation"],
        "document_version_id": "version-1",
        "workspace_id": "workspace-1",
        "language": "pl",
        "chunking_strategy_version": "markdown_semantic_v1",
    }


def test_embed_texts_rejects_unexpected_vector_count() -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"embeddings": [[1.0]]})))
    service = OllamaEmbeddingService(
        base_url="http://ollama:11434",
        model_name="nomic-embed-text",
        timeout_seconds=30,
        client=client,
    )

    with pytest.raises(EmbeddingProviderError):
        service.embed_texts(
            [
                EmbeddingInput(text="first", metadata={}),
                EmbeddingInput(text="second", metadata={}),
            ]
        )


def test_parse_ollama_embedding_response_supports_legacy_single_embedding() -> None:
    assert parse_ollama_embedding_response({"embedding": [1, "2.5"]}) == [[1.0, 2.5]]


def test_embed_query_rejects_empty_query() -> None:
    service = OllamaEmbeddingService(
        base_url="http://ollama:11434",
        model_name="nomic-embed-text",
        timeout_seconds=30,
        client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(500))),
    )

    with pytest.raises(ValueError):
        service.embed_query("   ")

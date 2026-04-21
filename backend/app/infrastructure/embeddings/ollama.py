from collections.abc import Iterable

import httpx

from app.core.config import Settings, get_settings
from app.domain.chunking.markdown import DocumentChunk
from app.domain.embeddings import EmbeddingInput, EmbeddingMetadata, EmbeddingResult


class EmbeddingProviderError(RuntimeError):
    pass


class OllamaEmbeddingService:
    provider = "ollama"

    def __init__(
        self,
        *,
        base_url: str,
        model_name: str,
        timeout_seconds: int,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self._client = client

    @classmethod
    def from_settings(cls, settings: Settings, *, client: httpx.Client | None = None) -> "OllamaEmbeddingService":
        return cls(
            base_url=f"http://{settings.ollama.host}:{settings.ollama.port}",
            model_name=settings.embeddings.model,
            timeout_seconds=settings.embeddings.timeout_seconds,
            client=client,
        )

    def embed_texts(self, inputs: list[EmbeddingInput]) -> list[EmbeddingResult]:
        if not inputs:
            return []

        texts = [item.text for item in inputs]
        embeddings = self._request_embeddings(texts)

        if len(embeddings) != len(inputs):
            raise EmbeddingProviderError("Embedding provider returned an unexpected number of vectors.")

        return [
            EmbeddingResult(
                vector=vector,
                metadata=self._metadata(vector),
                input_metadata=item.metadata,
            )
            for item, vector in zip(inputs, embeddings, strict=True)
        ]

    def embed_chunks(self, chunks: list[DocumentChunk]) -> list[EmbeddingResult]:
        return self.embed_texts(
            [
                EmbeddingInput(
                    text=chunk.text,
                    metadata={
                        "chunk_index": chunk.chunk_index,
                        "heading": chunk.heading,
                        "section_path": list(chunk.section_path),
                        "document_version_id": chunk.document_version_id,
                        "workspace_id": chunk.workspace_id,
                        "language": chunk.language,
                        "chunking_strategy_version": chunk.chunking_strategy_version,
                    },
                )
                for chunk in chunks
            ]
        )

    def embed_query(self, query: str) -> EmbeddingResult:
        stripped = query.strip()
        if not stripped:
            raise ValueError("Query text cannot be empty.")

        return self.embed_texts([EmbeddingInput(text=stripped, metadata={"input_type": "query"})])[0]

    def _request_embeddings(self, texts: list[str]) -> list[list[float]]:
        payload = {"model": self.model_name, "input": texts}
        client = self._client or httpx.Client(timeout=self.timeout_seconds)

        try:
            response = client.post(f"{self.base_url}/api/embed", json=payload)
            if response.status_code == 404:
                return self._request_legacy_embeddings(client=client, texts=texts)

            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise EmbeddingProviderError(f"Embedding provider request failed: {exc}") from exc
        finally:
            if self._client is None:
                client.close()

        return parse_ollama_embedding_response(response.json())

    def _request_legacy_embeddings(self, *, client: httpx.Client, texts: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []

        for text in texts:
            response = client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model_name, "prompt": text},
            )
            response.raise_for_status()
            parsed = parse_ollama_embedding_response(response.json())
            if len(parsed) != 1:
                raise EmbeddingProviderError("Legacy embedding provider returned an unexpected number of vectors.")
            embeddings.append(parsed[0])

        return embeddings

    def _metadata(self, vector: list[float]) -> EmbeddingMetadata:
        return EmbeddingMetadata(
            provider=self.provider,
            model_name=self.model_name,
            model_version=f"{self.provider}:{self.model_name}",
            dimensions=len(vector),
        )


def parse_ollama_embedding_response(payload: dict) -> list[list[float]]:
    embeddings = payload.get("embeddings")
    if isinstance(embeddings, list):
        return [parse_vector(vector) for vector in embeddings]

    embedding = payload.get("embedding")
    if isinstance(embedding, list):
        return [parse_vector(embedding)]

    raise EmbeddingProviderError("Embedding provider response did not include embeddings.")


def parse_vector(values: Iterable[object]) -> list[float]:
    try:
        vector = [float(value) for value in values]
    except (TypeError, ValueError) as exc:
        raise EmbeddingProviderError("Embedding vector contains non-numeric values.") from exc

    if not vector:
        raise EmbeddingProviderError("Embedding vector cannot be empty.")

    return vector


def get_embedding_service(settings: Settings | None = None) -> OllamaEmbeddingService:
    resolved_settings = settings or get_settings()
    if resolved_settings.embeddings.provider != "ollama":
        raise ValueError(f"Unsupported embedding provider: {resolved_settings.embeddings.provider}")

    return OllamaEmbeddingService.from_settings(resolved_settings)

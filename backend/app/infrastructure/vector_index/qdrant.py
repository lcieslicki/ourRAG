from collections.abc import Callable
from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

import httpx

from app.core.config import Settings, get_settings
from app.domain.embeddings import EmbeddingMetadata


class VectorIndexError(RuntimeError):
    pass


@dataclass(frozen=True)
class VectorPoint:
    chunk_id: str
    vector: list[float]
    workspace_id: str
    document_id: str
    document_version_id: str
    chunk_index: int
    text: str
    title: str
    category: str
    section_path: list[str]
    language: str
    is_active: bool
    embedding: EmbeddingMetadata
    tags: list[str] | None = None
    chunk_metadata: dict | None = None

    @property
    def point_id(self) -> str:
        return str(uuid5(NAMESPACE_URL, f"ourrag:{self.document_version_id}:{self.chunk_id}"))

    def payload(self) -> dict:
        payload = {
            "workspace_id": self.workspace_id,
            "document_id": self.document_id,
            "document_version_id": self.document_version_id,
            "chunk_id": self.chunk_id,
            "chunk_index": self.chunk_index,
            "text": self.text,
            "title": self.title,
            "category": self.category,
            "tags": self.tags or [],
            "section_path": self.section_path,
            "language": self.language,
            "is_active": self.is_active,
            "embedding_provider": self.embedding.provider,
            "embedding_model_name": self.embedding.model_name,
            "embedding_model_version": self.embedding.model_version,
            "embedding_dimensions": self.embedding.dimensions,
            "chunk_metadata": self.chunk_metadata or {},
            "chunk_type": (self.chunk_metadata or {}).get("chunk_type", "prose"),
            "source_format": (self.chunk_metadata or {}).get("source_format", "markdown"),
        }
        if self.chunk_metadata:
            for key in ("table_name", "row_key", "document_name", "section"):
                if key in self.chunk_metadata:
                    payload[key] = self.chunk_metadata[key]
        return payload


@dataclass(frozen=True)
class VectorIndexQuery:
    workspace_id: str
    vector: list[float]
    top_k: int
    category: str | None = None
    document_ids: list[str] | None = None
    language: str | None = None
    active_only: bool = True
    debug_hook: Callable[[str, dict], None] | None = None


@dataclass(frozen=True)
class VectorIndexResult:
    id: str
    score: float
    payload: dict


class QdrantVectorIndex:
    def __init__(
        self,
        *,
        base_url: str,
        collection: str,
        timeout_seconds: int,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.collection = collection
        self.timeout_seconds = timeout_seconds
        self._client = client

    @classmethod
    def from_settings(cls, settings: Settings, *, client: httpx.Client | None = None) -> "QdrantVectorIndex":
        return cls(
            base_url=f"http://{settings.qdrant.host}:{settings.qdrant.port}",
            collection=settings.qdrant.collection,
            timeout_seconds=settings.qdrant.timeout,
            client=client,
        )

    def ensure_collection(self, *, vector_size: int, distance: str = "Cosine") -> None:
        client = self._client or httpx.Client(timeout=self.timeout_seconds)
        collection_url = f"{self.base_url}/collections/{self.collection}"

        try:
            response = client.request("GET", collection_url)
            response.raise_for_status()
            return
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 404:
                raise VectorIndexError(f"Qdrant request failed: {exc}") from exc
        except httpx.HTTPError as exc:
            raise VectorIndexError(f"Qdrant request failed: {exc}") from exc
        finally:
            if self._client is None:
                client.close()

        payload = {"vectors": {"size": vector_size, "distance": distance}}
        self._request("PUT", f"/collections/{self.collection}", json=payload)

    def upsert_chunk_vectors(self, points: list[VectorPoint]) -> None:
        if not points:
            return

        payload = {
            "points": [
                {
                    "id": point.point_id,
                    "vector": point.vector,
                    "payload": point.payload(),
                }
                for point in points
            ]
        }
        self._request("PUT", f"/collections/{self.collection}/points", json=payload)

    def delete_document_version_vectors(self, *, workspace_id: str, document_version_id: str) -> None:
        self._request(
            "POST",
            f"/collections/{self.collection}/points/delete",
            json={
                "filter": {
                    "must": [
                        match_filter("workspace_id", workspace_id),
                        match_filter("document_version_id", document_version_id),
                    ]
                }
            },
        )

    def query(self, query: VectorIndexQuery) -> list[VectorIndexResult]:
        if query.top_k <= 0:
            raise ValueError("top_k must be positive.")
        if query.debug_hook:
            query.debug_hook(
                "retrieval.qdrant_query_started",
                {
                    "workspace_id": query.workspace_id,
                    "top_k": query.top_k,
                    "category": query.category,
                    "document_ids": query.document_ids,
                    "language": query.language,
                    "active_only": query.active_only,
                    "filter": build_retrieval_filter(query),
                },
            )

        response = self._request(
            "POST",
            f"/collections/{self.collection}/points/search",
            json={
                "vector": query.vector,
                "limit": query.top_k,
                "with_payload": True,
                "filter": build_retrieval_filter(query),
            },
        )
        results = response.get("result", [])
        if not isinstance(results, list):
            raise VectorIndexError("Qdrant search response did not include a result list.")

        if query.debug_hook:
            query.debug_hook(
                "retrieval.qdrant_query_completed",
                {
                    "result_count": len(results),
                    "results": results,
                },
            )

        return [
            VectorIndexResult(
                id=str(item["id"]),
                score=float(item["score"]),
                payload=dict(item.get("payload") or {}),
            )
            for item in results
        ]

    def count_document_version_vectors(
        self,
        *,
        workspace_id: str,
        document_version_id: str,
        active_only: bool = True,
    ) -> int:
        must: list[dict] = [
            match_filter("workspace_id", workspace_id),
            match_filter("document_version_id", document_version_id),
        ]
        if active_only:
            must.append(match_filter("is_active", True))
        response = self._request(
            "POST",
            f"/collections/{self.collection}/points/count",
            json={
                "exact": True,
                "filter": {"must": must},
            },
        )
        result = response.get("result")
        if not isinstance(result, dict):
            raise VectorIndexError("Qdrant count response did not include a result object.")
        count = result.get("count")
        if not isinstance(count, int):
            raise VectorIndexError("Qdrant count response did not include an integer count.")
        return count

    def _request(self, method: str, path: str, *, json: dict) -> dict:
        client = self._client or httpx.Client(timeout=self.timeout_seconds)

        try:
            response = client.request(method, f"{self.base_url}{path}", json=json)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise VectorIndexError(f"Qdrant request failed: {exc}") from exc
        finally:
            if self._client is None:
                client.close()

        return response.json() if response.content else {}


def build_retrieval_filter(query: VectorIndexQuery) -> dict:
    must = [match_filter("workspace_id", query.workspace_id)]

    if query.active_only:
        must.append(match_filter("is_active", True))

    if query.category:
        must.append(match_filter("category", query.category))

    if query.language:
        must.append(match_filter("language", query.language))

    if query.document_ids:
        must.append({"key": "document_id", "match": {"any": query.document_ids}})

    return {"must": must}


def match_filter(key: str, value: str | bool) -> dict:
    return {"key": key, "match": {"value": value}}


def get_vector_index(settings: Settings | None = None) -> QdrantVectorIndex:
    return QdrantVectorIndex.from_settings(settings or get_settings())

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.embeddings import EmbeddingService
from app.domain.errors import DocumentAccessDenied
from app.domain.models import Document
from app.domain.services.access import WorkspaceAccessService
from app.infrastructure.vector_index import VectorIndexQuery, VectorIndexResult


class VectorIndexService(Protocol):
    def query(self, query: VectorIndexQuery) -> list[VectorIndexResult]:
        pass


@dataclass(frozen=True)
class RetrievalScope:
    category: str | None = None
    document_ids: tuple[str, ...] = ()
    language: str | None = None


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    chunk_text: str
    document_id: str
    document_version_id: str
    document_title: str
    section_path: tuple[str, ...]
    score: float
    category: str | None
    language: str | None
    is_active: bool
    payload: dict


@dataclass(frozen=True)
class RetrievalResponse:
    workspace_id: str
    query: str
    chunks: tuple[RetrievedChunk, ...]


class RetrievalService:
    def __init__(
        self,
        *,
        session: Session,
        embedding_service: EmbeddingService,
        vector_index: VectorIndexService,
        settings: Settings,
        debug_hook: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        self.session = session
        self.embedding_service = embedding_service
        self.vector_index = vector_index
        self.settings = settings
        self.access = WorkspaceAccessService(session)
        self.debug_hook = debug_hook

    def retrieve(
        self,
        *,
        user_id: str,
        workspace_id: str,
        query: str,
        scope: RetrievalScope | None = None,
        top_k: int | None = None,
    ) -> RetrievalResponse:
        cleaned_query = query.strip()
        if not cleaned_query:
            raise ValueError("Retrieval query cannot be empty.")

        resolved_scope = scope or RetrievalScope()
        self.access.ensure_workspace_member(user_id=user_id, workspace_id=workspace_id)
        self._ensure_documents_in_workspace(
            workspace_id=workspace_id,
            document_ids=resolved_scope.document_ids,
        )

        self._emit(
            "retrieval.embedding_started",
            {"workspace_id": workspace_id, "query": cleaned_query},
        )
        query_embedding = self.embedding_service.embed_query(cleaned_query)
        self._emit(
            "retrieval.embedding_completed",
            {
                "embedding_metadata": {
                    "provider": query_embedding.metadata.provider,
                    "model_name": query_embedding.metadata.model_name,
                    "model_version": query_embedding.metadata.model_version,
                    "dimensions": query_embedding.metadata.dimensions,
                }
            },
        )
        candidate_count = top_k or self.settings.retrieval.top_k
        raw_results = self.vector_index.query(
            VectorIndexQuery(
                workspace_id=workspace_id,
                vector=query_embedding.vector,
                top_k=candidate_count,
                category=resolved_scope.category,
                document_ids=list(resolved_scope.document_ids) or None,
                language=resolved_scope.language,
                active_only=True,
                debug_hook=self.debug_hook,
            )
        )

        chunks = self._package_results(workspace_id=workspace_id, results=raw_results)
        self._emit(
            "retrieval.completed",
            {
                "workspace_id": workspace_id,
                "query": cleaned_query,
                "category": resolved_scope.category,
                "language": resolved_scope.language,
                "document_ids": list(resolved_scope.document_ids),
                "raw_result_count": len(raw_results),
                "chunk_count": len(chunks),
                "chunks": [chunk.payload for chunk in chunks],
            },
        )
        return RetrievalResponse(
            workspace_id=workspace_id,
            query=cleaned_query,
            chunks=tuple(chunks[: self.settings.retrieval.max_context_chunks]),
        )

    def _ensure_documents_in_workspace(self, *, workspace_id: str, document_ids: tuple[str, ...]) -> None:
        if not document_ids:
            return

        found_ids = set(
            self.session.scalars(
                select(Document.id).where(
                    Document.id.in_(document_ids),
                    Document.workspace_id == workspace_id,
                )
            )
        )
        requested_ids = set(document_ids)

        if found_ids != requested_ids:
            raise DocumentAccessDenied("One or more selected documents do not belong to the workspace.")

    def _package_results(self, *, workspace_id: str, results: list[VectorIndexResult]) -> list[RetrievedChunk]:
        chunks: list[RetrievedChunk] = []
        seen_chunk_ids: set[str] = set()

        for result in results:
            payload = result.payload
            if payload.get("workspace_id") != workspace_id:
                continue

            if payload.get("is_active") is not True:
                continue

            chunk_id = str(payload.get("chunk_id") or result.id)
            if chunk_id in seen_chunk_ids:
                continue

            seen_chunk_ids.add(chunk_id)
            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    chunk_text=str(payload.get("text") or ""),
                    document_id=str(payload.get("document_id") or ""),
                    document_version_id=str(payload.get("document_version_id") or ""),
                    document_title=str(payload.get("title") or ""),
                    section_path=tuple(payload.get("section_path") or ()),
                    score=result.score,
                    category=payload.get("category"),
                    language=payload.get("language"),
                    is_active=True,
                    payload=payload,
                )
            )

        return chunks

    def _emit(self, event: str, payload: dict[str, Any]) -> None:
        if self.debug_hook:
            self.debug_hook(event, payload)

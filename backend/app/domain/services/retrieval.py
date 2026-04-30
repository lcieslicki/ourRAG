from dataclasses import dataclass
from typing import Any, Callable, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.embeddings import EmbeddingService
from app.domain.errors import DocumentAccessDenied
from app.domain.models import Document, DocumentVersion
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
        active_versions = self._active_version_document_ids(workspace_id=workspace_id, results=results)

        for result in results:
            payload = result.payload
            if payload.get("workspace_id") != workspace_id:
                continue

            if payload.get("is_active") is not True:
                continue

            document_version_id = str(payload.get("document_version_id") or "")
            document_id = str(payload.get("document_id") or "")
            if active_versions.get(document_version_id) != document_id:
                continue

            chunk_id = str(payload.get("chunk_id") or result.id)
            if chunk_id in seen_chunk_ids:
                continue

            seen_chunk_ids.add(chunk_id)
            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    chunk_text=str(payload.get("text") or ""),
                    document_id=document_id,
                    document_version_id=document_version_id,
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

    def _active_version_document_ids(self, *, workspace_id: str, results: list[VectorIndexResult]) -> dict[str, str]:
        version_ids = {
            str(result.payload.get("document_version_id"))
            for result in results
            if result.payload.get("workspace_id") == workspace_id and result.payload.get("document_version_id")
        }
        if not version_ids:
            return {}

        rows = self.session.execute(
            select(DocumentVersion.id, DocumentVersion.document_id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(
                Document.workspace_id == workspace_id,
                Document.status == "active",
                DocumentVersion.id.in_(version_ids),
                DocumentVersion.is_active.is_(True),
                DocumentVersion.is_invalidated.is_(False),
                DocumentVersion.processing_status == "ready",
            )
        )
        return {version_id: document_id for version_id, document_id in rows}

    def _emit(self, event: str, payload: dict[str, Any]) -> None:
        if self.debug_hook:
            self.debug_hook(event, payload)

    def retrieve_with_rewrite_plan(
        self,
        *,
        user_id: str,
        workspace_id: str,
        query: str,
        rewrite_plan: "RewritePlan | None" = None,
        scope: RetrievalScope | None = None,
        top_k: int | None = None,
    ) -> RetrievalResponse:
        """Retrieve using a rewrite plan if provided, otherwise use original query.

        This method provides optional support for query rewriting without breaking
        existing single-query retrieval. If rewrite_plan is None or mode is disabled,
        falls back to standard retrieve() behavior.

        Args:
            user_id: User ID for access control.
            workspace_id: Workspace ID to scope retrieval.
            query: Original query (fallback if no rewrite_plan).
            rewrite_plan: Optional RewritePlan with rewritten queries.
            scope: Optional retrieval scope (category, language, documents).
            top_k: Optional override for number of results.

        Returns:
            RetrievalResponse with chunks for the given queries.
        """
        # Import here to avoid circular dependency
        from app.domain.query_rewriting.models import QueryRewriteMode

        # If no rewrite plan or disabled mode, use standard retrieve
        if rewrite_plan is None or rewrite_plan.mode == QueryRewriteMode.DISABLED:
            return self.retrieve(
                user_id=user_id,
                workspace_id=workspace_id,
                query=query,
                scope=scope,
                top_k=top_k,
            )

        # Multi-query retrieval: use all queries from the plan
        all_chunks = []
        seen_chunk_ids = set()

        for query_text in rewrite_plan.all_queries:
            try:
                response = self.retrieve(
                    user_id=user_id,
                    workspace_id=workspace_id,
                    query=query_text,
                    scope=scope,
                    top_k=top_k,
                )

                # Merge results, keeping highest score per chunk_id
                for chunk in response.chunks:
                    if chunk.chunk_id not in seen_chunk_ids:
                        all_chunks.append(chunk)
                        seen_chunk_ids.add(chunk.chunk_id)
                    else:
                        # Replace if this score is higher
                        for i, existing in enumerate(all_chunks):
                            if existing.chunk_id == chunk.chunk_id and chunk.score > existing.score:
                                all_chunks[i] = chunk
                                break

            except Exception:
                # Continue with next query on error
                continue

        # Sort by score descending
        all_chunks.sort(key=lambda c: c.score, reverse=True)

        return RetrievalResponse(
            workspace_id=workspace_id,
            query=query,
            chunks=tuple(all_chunks[: self.settings.retrieval.max_context_chunks]),
        )

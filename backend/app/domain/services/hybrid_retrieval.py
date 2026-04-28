"""
Hybrid retrieval service (A2).

Combines semantic (Qdrant) and lexical (PostgreSQL FTS) retrieval,
normalizes scores and merges results deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.embeddings import EmbeddingService
from app.domain.models import Document, DocumentVersion
from app.domain.services.access import WorkspaceAccessService
from app.domain.services.retrieval import (
    RetrievalResponse,
    RetrievalScope,
    RetrievedChunk,
    VectorIndexService,
)
from app.infrastructure.vector_index import VectorIndexQuery


@dataclass(frozen=True)
class LexicalCandidate:
    chunk_id: str
    chunk_text: str
    document_id: str
    document_version_id: str
    document_title: str
    section_path: tuple[str, ...]
    heading: str | None
    category: str | None
    language: str | None
    rank: float  # raw PG ts_rank score


@dataclass(frozen=True)
class HybridCandidate:
    chunk_id: str
    chunk_text: str
    document_id: str
    document_version_id: str
    document_title: str
    section_path: tuple[str, ...]
    heading: str | None
    category: str | None
    language: str | None
    # scores
    semantic_score: float | None
    lexical_score: float | None
    merged_score: float
    retrieval_channels: tuple[str, ...]  # ("semantic",) | ("lexical",) | ("semantic", "lexical")
    payload: dict = field(default_factory=dict)


class LexicalRetriever:
    """Retrieves chunks via PostgreSQL full-text search."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def retrieve(
        self,
        *,
        workspace_id: str,
        query: str,
        top_k: int,
        scope: RetrievalScope,
        active_version_ids: set[str],
    ) -> list[LexicalCandidate]:
        if not query.strip():
            return []

        # Build ts_query from the plain query (simple dictionary = language-agnostic)
        params: dict[str, Any] = {
            "ws_id": workspace_id,
            "query_text": query,
            "top_k": top_k,
        }

        where_clauses = [
            "dc.workspace_id = :ws_id",
            "dc.is_active = true",
            "dc.search_vector @@ plainto_tsquery('simple', :query_text)",
        ]

        if active_version_ids:
            params["active_version_ids"] = list(active_version_ids)
            where_clauses.append("dc.document_version_id = ANY(:active_version_ids)")

        if scope.category:
            params["category"] = scope.category
            where_clauses.append("dc.category = :category")

        if scope.language:
            params["language"] = scope.language
            where_clauses.append("dc.language = :language")

        if scope.document_ids:
            params["doc_ids"] = list(scope.document_ids)
            where_clauses.append("dc.document_id = ANY(:doc_ids)")

        where_sql = " AND ".join(where_clauses)

        sql = text(f"""
            SELECT
                dc.chunk_id,
                dc.chunk_text,
                dc.document_id,
                dc.document_version_id,
                dc.document_title,
                dc.section_path_text,
                dc.heading,
                dc.category,
                dc.language,
                ts_rank(dc.search_vector, plainto_tsquery('simple', :query_text)) AS rank
            FROM document_chunks dc
            WHERE {where_sql}
            ORDER BY rank DESC
            LIMIT :top_k
        """)

        rows = self.session.execute(sql, params).fetchall()

        return [
            LexicalCandidate(
                chunk_id=row.chunk_id,
                chunk_text=row.chunk_text,
                document_id=row.document_id,
                document_version_id=row.document_version_id,
                document_title=row.document_title or "",
                section_path=tuple(row.section_path_text.split(" > ")) if row.section_path_text else (),
                heading=row.heading,
                category=row.category,
                language=row.language,
                rank=float(row.rank),
            )
            for row in rows
        ]


class HybridRetrievalService:
    """
    Fetches candidates from both semantic and lexical channels,
    normalizes scores, and merges them deterministically.
    """

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
    ) -> RetrievalResponse:
        cleaned_query = query.strip()
        if not cleaned_query:
            raise ValueError("Retrieval query cannot be empty.")

        resolved_scope = scope or RetrievalScope()
        self.access.ensure_workspace_member(user_id=user_id, workspace_id=workspace_id)

        cfg = self.settings.hybrid_retrieval

        # ── Semantic retrieval ────────────────────────────────────────────
        self._emit("retrieval.semantic_started", {"query": cleaned_query})
        query_embedding = self.embedding_service.embed_query(cleaned_query)
        semantic_results = self.vector_index.query(
            VectorIndexQuery(
                workspace_id=workspace_id,
                vector=query_embedding.vector,
                top_k=cfg.semantic_top_k,
                category=resolved_scope.category,
                document_ids=list(resolved_scope.document_ids) or None,
                language=resolved_scope.language,
                active_only=True,
                debug_hook=self.debug_hook,
            )
        )
        self._emit(
            "retrieval.semantic_completed",
            {"result_count": len(semantic_results)},
        )

        # ── Active version lookup ─────────────────────────────────────────
        active_versions = self._active_version_ids(workspace_id=workspace_id)

        # ── Lexical retrieval (with graceful fallback) ─────────────────────
        lexical_candidates: list[LexicalCandidate] = []
        if cfg.mode == "hybrid":
            try:
                self._emit("retrieval.lexical_started", {"query": cleaned_query})
                lexical_candidates = LexicalRetriever(self.session).retrieve(
                    workspace_id=workspace_id,
                    query=cleaned_query,
                    top_k=cfg.lexical_top_k,
                    scope=resolved_scope,
                    active_version_ids=active_versions,
                )
                self._emit(
                    "retrieval.lexical_completed",
                    {"result_count": len(lexical_candidates)},
                )
            except Exception as exc:
                self._emit(
                    "retrieval.lexical_fallback",
                    {"error": type(exc).__name__, "message": str(exc)},
                )
                # Fallback: continue with semantic-only results

        # ── Build semantic map ─────────────────────────────────────────────
        semantic_map: dict[str, tuple[float, Any]] = {}  # chunk_id -> (score, raw_result)
        for result in semantic_results:
            chunk_id = str(result.payload.get("chunk_id") or result.id)
            if result.payload.get("workspace_id") != workspace_id:
                continue
            if result.payload.get("is_active") is not True:
                continue
            ver_id = str(result.payload.get("document_version_id") or "")
            if ver_id not in active_versions:
                continue
            if chunk_id not in semantic_map:
                semantic_map[chunk_id] = (result.score, result)

        # ── Build lexical map ──────────────────────────────────────────────
        lexical_map: dict[str, LexicalCandidate] = {}
        for cand in lexical_candidates:
            if cand.document_version_id in active_versions:
                if cand.chunk_id not in lexical_map:
                    lexical_map[cand.chunk_id] = cand

        # ── Merge ──────────────────────────────────────────────────────────
        all_chunk_ids = list(semantic_map.keys()) + [
            cid for cid in lexical_map if cid not in semantic_map
        ]

        sem_scores = [semantic_map[cid][0] for cid in all_chunk_ids if cid in semantic_map]
        lex_scores = [lexical_map[cid].rank for cid in all_chunk_ids if cid in lexical_map]

        sem_min, sem_max = (min(sem_scores), max(sem_scores)) if sem_scores else (0.0, 1.0)
        lex_min, lex_max = (min(lex_scores), max(lex_scores)) if lex_scores else (0.0, 1.0)

        def norm(val: float, mn: float, mx: float) -> float:
            if mx == mn:
                return 1.0
            return (val - mn) / (mx - mn)

        merged: list[HybridCandidate] = []
        for chunk_id in all_chunk_ids:
            has_sem = chunk_id in semantic_map
            has_lex = chunk_id in lexical_map

            sem_raw = semantic_map[chunk_id][0] if has_sem else None
            lex_raw = lexical_map[chunk_id].rank if has_lex else None

            sem_norm = norm(sem_raw, sem_min, sem_max) if sem_raw is not None else 0.0
            lex_norm = norm(lex_raw, lex_min, lex_max) if lex_raw is not None else 0.0

            merged_score = cfg.semantic_weight * sem_norm + cfg.lexical_weight * lex_norm

            channels: list[str] = []
            if has_sem:
                channels.append("semantic")
            if has_lex:
                channels.append("lexical")

            if has_sem:
                raw = semantic_map[chunk_id][1]
                payload = raw.payload
                merged.append(
                    HybridCandidate(
                        chunk_id=chunk_id,
                        chunk_text=str(payload.get("text") or ""),
                        document_id=str(payload.get("document_id") or ""),
                        document_version_id=str(payload.get("document_version_id") or ""),
                        document_title=str(payload.get("title") or ""),
                        section_path=tuple(payload.get("section_path") or ()),
                        heading=None,
                        category=payload.get("category"),
                        language=payload.get("language"),
                        semantic_score=sem_raw,
                        lexical_score=lex_raw,
                        merged_score=merged_score,
                        retrieval_channels=tuple(channels),
                        payload=payload,
                    )
                )
            else:
                lex_cand = lexical_map[chunk_id]
                merged.append(
                    HybridCandidate(
                        chunk_id=chunk_id,
                        chunk_text=lex_cand.chunk_text,
                        document_id=lex_cand.document_id,
                        document_version_id=lex_cand.document_version_id,
                        document_title=lex_cand.document_title,
                        section_path=lex_cand.section_path,
                        heading=lex_cand.heading,
                        category=lex_cand.category,
                        language=lex_cand.language,
                        semantic_score=None,
                        lexical_score=lex_raw,
                        merged_score=merged_score,
                        retrieval_channels=tuple(channels),
                        payload={},
                    )
                )

        # Deterministic sort: merged_score desc, semantic desc, lexical desc, chunk_id asc
        merged.sort(
            key=lambda c: (
                -c.merged_score,
                -(c.semantic_score or 0.0),
                -(c.lexical_score or 0.0),
                c.chunk_id,
            )
        )

        final = merged[: cfg.final_top_k]

        self._emit(
            "retrieval.hybrid_completed",
            {
                "workspace_id": workspace_id,
                "mode": cfg.mode,
                "semantic_count": len(semantic_map),
                "lexical_count": len(lexical_map),
                "merged_count": len(merged),
                "final_count": len(final),
            },
        )

        chunks = tuple(
            RetrievedChunk(
                chunk_id=c.chunk_id,
                chunk_text=c.chunk_text,
                document_id=c.document_id,
                document_version_id=c.document_version_id,
                document_title=c.document_title,
                section_path=c.section_path,
                score=c.merged_score,
                category=c.category,
                language=c.language,
                is_active=True,
                payload={
                    **c.payload,
                    "retrieval_channels": list(c.retrieval_channels),
                    "semantic_score": c.semantic_score,
                    "lexical_score": c.lexical_score,
                    "merged_score": c.merged_score,
                },
            )
            for c in final
        )

        return RetrievalResponse(
            workspace_id=workspace_id,
            query=cleaned_query,
            chunks=chunks,
        )

    def _active_version_ids(self, *, workspace_id: str) -> set[str]:
        rows = self.session.scalars(
            select(DocumentVersion.id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(
                Document.workspace_id == workspace_id,
                Document.status == "active",
                DocumentVersion.is_active.is_(True),
                DocumentVersion.is_invalidated.is_(False),
                DocumentVersion.processing_status == "ready",
            )
        )
        return set(rows)

    def _emit(self, event: str, payload: dict[str, Any]) -> None:
        if self.debug_hook:
            self.debug_hook(event, payload)

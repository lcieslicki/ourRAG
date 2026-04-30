import logging
from typing import Any, Optional

from app.core.config.query_rewrite_config import QueryRewriteConfig
from app.domain.services.retrieval import RetrievalScope, RetrievalService
from .models import QueryRewriteMode, RewritePlan

logger = logging.getLogger(__name__)


class MultiQueryRetrievalService:
    """Service for retrieving chunks using multiple query phrasings.

    This service:
    1. Takes a RewritePlan with multiple query phrasings.
    2. Runs retrieval for each query independently.
    3. Merges and deduplicates results by chunk_id.
    4. Tracks which queries matched each chunk.
    5. Returns merged, sorted results.

    Attributes:
        retrieval_service: The underlying retrieval service.
        settings: Query rewriting configuration.
    """

    def __init__(
        self,
        retrieval_service: RetrievalService,
        settings: QueryRewriteConfig,
    ) -> None:
        self.retrieval_service = retrieval_service
        self.settings = settings

    async def retrieve(
        self,
        rewrite_plan: RewritePlan,
        *,
        user_id: str,
        workspace_id: str,
        scope: Optional[RetrievalScope] = None,
        top_k: Optional[int] = None,
    ) -> dict[str, Any]:
        """Retrieve chunks using multiple query phrasings.

        Args:
            rewrite_plan: Plan with original, contextualized, and rewritten queries.
            user_id: User ID for access control.
            workspace_id: Workspace ID to scope retrieval.
            scope: Optional retrieval scope (category, language, documents).
            top_k: Optional override for number of results.

        Returns:
            Dictionary with:
            - chunks: List of deduplicated, merged chunks sorted by score.
            - debug: Debug info with query plan and which_query_matched per chunk.
        """
        # If mode is disabled or no queries, use original query only
        if rewrite_plan.mode == QueryRewriteMode.DISABLED:
            queries_to_retrieve = [rewrite_plan.original_query]
        else:
            queries_to_retrieve = rewrite_plan.all_queries

        all_results = {}  # chunk_id -> highest-scoring result
        query_matches = {}  # chunk_id -> list of queries that matched

        # Retrieve for each query
        for query_text in queries_to_retrieve:
            try:
                response = self.retrieval_service.retrieve(
                    user_id=user_id,
                    workspace_id=workspace_id,
                    query=query_text,
                    scope=scope,
                    top_k=top_k,
                )

                # Merge results
                for chunk in response.chunks:
                    chunk_id = chunk.chunk_id

                    # Keep the highest-scoring version
                    if chunk_id not in all_results or chunk.score > all_results[chunk_id]["score"]:
                        all_results[chunk_id] = self._chunk_to_dict(chunk)

                    # Track which queries matched this chunk
                    if chunk_id not in query_matches:
                        query_matches[chunk_id] = []
                    if query_text not in query_matches[chunk_id]:
                        query_matches[chunk_id].append(query_text)

            except Exception as e:
                logger.error(f"Retrieval failed for query '{query_text}': {e}")
                continue

        # Sort by score descending
        merged_chunks = sorted(all_results.values(), key=lambda x: x["score"], reverse=True)

        # Attach debug info (which queries matched each chunk)
        for chunk in merged_chunks:
            chunk_id = chunk["chunk_id"]
            chunk["which_query_matched"] = query_matches.get(chunk_id, [])

        return {
            "chunks": merged_chunks,
            "debug": {
                "original_query": rewrite_plan.original_query,
                "contextualized_query": rewrite_plan.contextualized_query,
                "rewritten_queries": rewrite_plan.rewritten_queries,
                "all_queries_used": queries_to_retrieve,
                "total_chunks_after_merge": len(merged_chunks),
            },
        }

    @staticmethod
    def _chunk_to_dict(chunk) -> dict[str, Any]:
        """Convert RetrievedChunk dataclass to dict for merging.

        Args:
            chunk: RetrievedChunk dataclass.

        Returns:
            Dictionary representation of chunk with all fields.
        """
        return {
            "chunk_id": chunk.chunk_id,
            "chunk_text": chunk.chunk_text,
            "document_id": chunk.document_id,
            "document_version_id": chunk.document_version_id,
            "document_title": chunk.document_title,
            "section_path": chunk.section_path,
            "score": chunk.score,
            "category": chunk.category,
            "language": chunk.language,
            "is_active": chunk.is_active,
            "payload": chunk.payload,
        }

    @staticmethod
    def _deduplicate(candidates: list[dict]) -> list[dict]:
        """Deduplicate chunks by chunk_id, keeping highest score.

        Args:
            candidates: List of chunk dictionaries.

        Returns:
            Deduplicated list, sorted by score descending.
        """
        seen = {}
        for chunk in candidates:
            chunk_id = chunk["chunk_id"]
            if chunk_id not in seen or chunk["score"] > seen[chunk_id]["score"]:
                seen[chunk_id] = chunk

        return sorted(seen.values(), key=lambda x: x["score"], reverse=True)

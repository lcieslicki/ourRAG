"""
Reranking service and provider abstraction (A3).

Position in pipeline: after retrieval, before prompt assembly.
Reranking may only reorder/drop candidates — never introduce new ones.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Protocol, Sequence

from app.domain.services.retrieval import RetrievedChunk

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScoredCandidate:
    chunk: RetrievedChunk
    original_rank: int
    rerank_score: float
    final_rank: int


class RerankingProvider(Protocol):
    """Abstract reranking provider interface."""

    def rerank(
        self,
        query: str,
        candidates: Sequence[RetrievedChunk],
    ) -> list[ScoredCandidate]:
        """
        Reranks candidates for the given query.

        Must return a subset (or all) of input candidates in new order.
        Must NOT introduce new chunks.
        """
        ...


class LocalCrossEncoderReranker:
    """
    Local cross-encoder reranker using sentence-transformers.

    Falls back gracefully if the model is unavailable.
    Uses 'cross-encoder/ms-marco-MiniLM-L-6-v2' by default (multilingual-capable).
    """

    _model: object | None = None
    _model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def _get_model(self) -> object | None:
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import CrossEncoder  # type: ignore

            self.__class__._model = CrossEncoder(self._model_name)
            return self.__class__._model
        except Exception as exc:
            logger.warning("LocalCrossEncoderReranker: failed to load model: %s", exc)
            return None

    def rerank(
        self,
        query: str,
        candidates: Sequence[RetrievedChunk],
    ) -> list[ScoredCandidate]:
        model = self._get_model()
        if model is None:
            # Fallback: return original ordering
            return _identity_scores(candidates)

        try:
            pairs = [(query, chunk.chunk_text) for chunk in candidates]
            scores = model.predict(pairs)  # type: ignore[attr-defined]
        except Exception as exc:
            logger.warning("LocalCrossEncoderReranker: prediction failed: %s", exc)
            return _identity_scores(candidates)

        indexed = list(zip(candidates, scores))
        # Sort by score descending, tie-break by original position ascending (deterministic)
        indexed.sort(key=lambda x: (-x[1], candidates.index(x[0])))

        return [
            ScoredCandidate(
                chunk=chunk,
                original_rank=list(candidates).index(chunk) + 1,
                rerank_score=float(score),
                final_rank=final_rank,
            )
            for final_rank, (chunk, score) in enumerate(indexed, start=1)
        ]


class SimpleScoreReranker:
    """
    Lightweight deterministic reranker for testing:
    scores by simple keyword overlap (no external dependencies).
    """

    def rerank(
        self,
        query: str,
        candidates: Sequence[RetrievedChunk],
    ) -> list[ScoredCandidate]:
        query_terms = set(query.lower().split())
        scored: list[tuple[RetrievedChunk, float, int]] = []
        for idx, chunk in enumerate(candidates):
            chunk_terms = set(chunk.chunk_text.lower().split())
            overlap = len(query_terms & chunk_terms)
            score = overlap / max(len(query_terms), 1) + chunk.score * 0.5
            scored.append((chunk, score, idx))

        scored.sort(key=lambda x: (-x[1], x[2]))

        return [
            ScoredCandidate(
                chunk=chunk,
                original_rank=orig_idx + 1,
                rerank_score=score,
                final_rank=final_rank,
            )
            for final_rank, (chunk, score, orig_idx) in enumerate(scored, start=1)
        ]


class RerankingService:
    """
    Applies optional reranking after retrieval.

    - If reranking is disabled or times out, falls back to upstream order.
    - Never introduces new chunks.
    - Respects final_top_k limit.
    """

    def __init__(
        self,
        *,
        provider: RerankingProvider,
        enabled: bool = True,
        timeout_ms: int = 800,
        fail_open: bool = True,
        final_top_k: int = 6,
    ) -> None:
        self.provider = provider
        self.enabled = enabled
        self.timeout_ms = timeout_ms
        self.fail_open = fail_open
        self.final_top_k = final_top_k

    def rerank(
        self,
        query: str,
        candidates: Sequence[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        """
        Returns final ordered list of chunks.
        On failure/timeout falls back to upstream order (fail_open=True).
        """
        if not candidates:
            return []

        if not self.enabled:
            return list(candidates)[: self.final_top_k]

        start_ms = time.monotonic() * 1000

        try:
            scored = self.provider.rerank(query, candidates)

            elapsed_ms = time.monotonic() * 1000 - start_ms
            if elapsed_ms > self.timeout_ms:
                logger.warning(
                    "reranking.timeout elapsed_ms=%.1f timeout_ms=%d",
                    elapsed_ms,
                    self.timeout_ms,
                )
                if self.fail_open:
                    return list(candidates)[: self.final_top_k]

            return [sc.chunk for sc in scored][: self.final_top_k]

        except Exception as exc:
            logger.warning("reranking.failed error=%s", exc)
            if self.fail_open:
                return list(candidates)[: self.final_top_k]
            raise


def _identity_scores(candidates: Sequence[RetrievedChunk]) -> list[ScoredCandidate]:
    """Returns candidates in original order with their retrieval scores."""
    return [
        ScoredCandidate(
            chunk=chunk,
            original_rank=idx + 1,
            rerank_score=chunk.score,
            final_rank=idx + 1,
        )
        for idx, chunk in enumerate(candidates)
    ]

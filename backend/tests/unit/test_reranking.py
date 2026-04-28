"""Unit tests for reranking service (A3)."""

import pytest

from app.domain.reranking.service import (
    RerankingService,
    ScoredCandidate,
    SimpleScoreReranker,
    _identity_scores,
)
from app.domain.services.retrieval import RetrievedChunk


def make_chunk(
    chunk_id: str,
    chunk_text: str = "default text",
    score: float = 0.8,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        chunk_text=chunk_text,
        document_id="doc-1",
        document_version_id="ver-1",
        document_title="Test",
        section_path=("Section",),
        score=score,
        category="HR",
        language="pl",
        is_active=True,
        payload={},
    )


# ── identity scores ───────────────────────────────────────────────────────────

def test_identity_scores_preserves_order_and_assigns_ranks() -> None:
    chunks = [make_chunk("a"), make_chunk("b"), make_chunk("c")]
    scored = _identity_scores(chunks)
    assert [s.chunk.chunk_id for s in scored] == ["a", "b", "c"]
    assert [s.final_rank for s in scored] == [1, 2, 3]
    assert [s.original_rank for s in scored] == [1, 2, 3]


# ── SimpleScoreReranker ordering ─────────────────────────────────────────────

def test_simple_reranker_reorders_by_keyword_overlap() -> None:
    chunks = [
        make_chunk("low", chunk_text="unrelated content here", score=0.5),
        make_chunk("high", chunk_text="urlop vacation policy leave days", score=0.5),
    ]
    reranker = SimpleScoreReranker()
    scored = reranker.rerank("urlop vacation", chunks)
    # "high" chunk has more keyword overlap, should rank first
    assert scored[0].chunk.chunk_id == "high"
    assert scored[0].final_rank == 1


def test_simple_reranker_tie_broken_by_original_position() -> None:
    # Both chunks have zero overlap with query
    chunks = [
        make_chunk("first", chunk_text="xyz xyz", score=0.8),
        make_chunk("second", chunk_text="xyz xyz", score=0.8),
    ]
    reranker = SimpleScoreReranker()
    scored = reranker.rerank("aaa bbb", chunks)
    # Same overlap (0), same base score → tie-break by original index
    assert scored[0].chunk.chunk_id == "first"


# ── RerankingService disabled ─────────────────────────────────────────────────

def test_reranking_disabled_returns_original_order_with_top_k() -> None:
    chunks = [make_chunk(f"c{i}") for i in range(10)]
    svc = RerankingService(
        provider=SimpleScoreReranker(),
        enabled=False,
        final_top_k=3,
    )
    result = svc.rerank("query", chunks)
    assert [c.chunk_id for c in result] == ["c0", "c1", "c2"]


def test_reranking_disabled_returns_all_when_top_k_large() -> None:
    chunks = [make_chunk(f"c{i}") for i in range(5)]
    svc = RerankingService(provider=SimpleScoreReranker(), enabled=False, final_top_k=20)
    result = svc.rerank("query", chunks)
    assert len(result) == 5


# ── RerankingService — final_top_k ────────────────────────────────────────────

def test_reranking_respects_final_top_k() -> None:
    chunks = [make_chunk(f"c{i}") for i in range(10)]
    svc = RerankingService(provider=SimpleScoreReranker(), enabled=True, final_top_k=4)
    result = svc.rerank("query", chunks)
    assert len(result) == 4


# ── RerankingService — empty input ────────────────────────────────────────────

def test_reranking_empty_input_returns_empty() -> None:
    svc = RerankingService(provider=SimpleScoreReranker(), enabled=True, final_top_k=6)
    result = svc.rerank("query", [])
    assert result == []


# ── RerankingService — fail_open ──────────────────────────────────────────────

class BrokenProvider:
    def rerank(self, query, candidates):
        raise RuntimeError("Provider exploded!")


def test_reranking_fail_open_returns_original_order_on_failure() -> None:
    chunks = [make_chunk("a"), make_chunk("b"), make_chunk("c")]
    svc = RerankingService(
        provider=BrokenProvider(),
        enabled=True,
        fail_open=True,
        final_top_k=3,
    )
    result = svc.rerank("query", chunks)
    assert [c.chunk_id for c in result] == ["a", "b", "c"]


def test_reranking_fail_closed_raises_on_failure() -> None:
    chunks = [make_chunk("a")]
    svc = RerankingService(
        provider=BrokenProvider(),
        enabled=True,
        fail_open=False,
        final_top_k=3,
    )
    with pytest.raises(RuntimeError):
        svc.rerank("query", chunks)


# ── ScoredCandidate is frozen ─────────────────────────────────────────────────

def test_scored_candidate_is_frozen() -> None:
    sc = ScoredCandidate(
        chunk=make_chunk("c1"),
        original_rank=1,
        rerank_score=0.9,
        final_rank=1,
    )
    with pytest.raises((AttributeError, TypeError)):
        sc.final_rank = 99  # type: ignore[misc]

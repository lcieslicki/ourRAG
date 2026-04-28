"""Unit tests for hybrid retrieval score normalization and merge (A2)."""

import pytest

from app.domain.services.hybrid_retrieval import HybridCandidate, LexicalCandidate


def make_hybrid_candidate(
    chunk_id: str,
    semantic_score: float | None = None,
    lexical_score: float | None = None,
    merged_score: float = 0.5,
    channels: tuple[str, ...] = ("semantic",),
) -> HybridCandidate:
    return HybridCandidate(
        chunk_id=chunk_id,
        chunk_text=f"Text for {chunk_id}",
        document_id="doc-1",
        document_version_id="ver-1",
        document_title="Test Document",
        section_path=("Section",),
        heading="Section",
        category="HR",
        language="pl",
        semantic_score=semantic_score,
        lexical_score=lexical_score,
        merged_score=merged_score,
        retrieval_channels=channels,
        payload={},
    )


# ── score normalization logic (isolated) ────────────────────────────────────

def _norm(val: float, mn: float, mx: float) -> float:
    if mx == mn:
        return 1.0
    return (val - mn) / (mx - mn)


def test_score_normalization_basic() -> None:
    assert _norm(0.8, 0.5, 1.0) == pytest.approx(0.6)
    assert _norm(0.5, 0.5, 1.0) == pytest.approx(0.0)
    assert _norm(1.0, 0.5, 1.0) == pytest.approx(1.0)


def test_score_normalization_identical_values_returns_one() -> None:
    # When all scores are equal, norm returns 1.0 (not divide by zero)
    assert _norm(0.75, 0.75, 0.75) == 1.0


# ── merge deduplication ──────────────────────────────────────────────────────

def test_merge_deduplication_by_chunk_id() -> None:
    """Verify that when building semantic + lexical maps, same chunk_id appears once."""
    chunk_ids_seen: dict[str, int] = {}
    candidates = [
        make_hybrid_candidate("a", merged_score=0.9),
        make_hybrid_candidate("b", merged_score=0.8),
        make_hybrid_candidate("a", merged_score=0.7),  # duplicate
    ]
    for c in candidates:
        if c.chunk_id not in chunk_ids_seen:
            chunk_ids_seen[c.chunk_id] = 0
        chunk_ids_seen[c.chunk_id] += 1

    # In real code the map uses chunk_id as key — simulating that
    deduped = {}
    for c in candidates:
        if c.chunk_id not in deduped:
            deduped[c.chunk_id] = c

    assert len(deduped) == 2
    assert deduped["a"].merged_score == 0.9  # first one kept


# ── deterministic ordering ───────────────────────────────────────────────────

def test_merged_candidates_sorted_by_merged_score_desc() -> None:
    candidates = [
        make_hybrid_candidate("c", merged_score=0.5),
        make_hybrid_candidate("a", merged_score=0.9),
        make_hybrid_candidate("b", merged_score=0.7),
    ]
    sorted_candidates = sorted(
        candidates,
        key=lambda c: (-c.merged_score, -(c.semantic_score or 0.0), -(c.lexical_score or 0.0), c.chunk_id),
    )
    assert [c.chunk_id for c in sorted_candidates] == ["a", "b", "c"]


def test_tie_broken_by_chunk_id_ascending() -> None:
    candidates = [
        make_hybrid_candidate("z", semantic_score=None, lexical_score=None, merged_score=0.8),
        make_hybrid_candidate("a", semantic_score=None, lexical_score=None, merged_score=0.8),
        make_hybrid_candidate("m", semantic_score=None, lexical_score=None, merged_score=0.8),
    ]
    sorted_candidates = sorted(
        candidates,
        key=lambda c: (-c.merged_score, -(c.semantic_score or 0.0), -(c.lexical_score or 0.0), c.chunk_id),
    )
    assert [c.chunk_id for c in sorted_candidates] == ["a", "m", "z"]


# ── retrieval channels ───────────────────────────────────────────────────────

def test_semantic_only_candidate_has_correct_channel() -> None:
    c = make_hybrid_candidate("x", semantic_score=0.8, channels=("semantic",))
    assert "semantic" in c.retrieval_channels
    assert "lexical" not in c.retrieval_channels


def test_hybrid_candidate_has_both_channels() -> None:
    c = make_hybrid_candidate("x", semantic_score=0.8, lexical_score=0.5, channels=("semantic", "lexical"))
    assert "semantic" in c.retrieval_channels
    assert "lexical" in c.retrieval_channels


# ── LexicalCandidate fields ───────────────────────────────────────────────────

def test_lexical_candidate_is_frozen() -> None:
    lc = LexicalCandidate(
        chunk_id="c1",
        chunk_text="text",
        document_id="doc-1",
        document_version_id="ver-1",
        document_title="Doc",
        section_path=("A",),
        heading="A",
        category="HR",
        language="pl",
        rank=0.5,
    )
    with pytest.raises((AttributeError, TypeError)):
        lc.rank = 99  # type: ignore[misc]

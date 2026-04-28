"""Unit tests for citation service (A1 — Citations Hardening)."""

import pytest

from app.domain.citations.service import CitationDTO, CitationService
from app.domain.services.retrieval import RetrievedChunk


def make_chunk(
    *,
    chunk_id: str = "chunk-1",
    document_id: str = "doc-1",
    document_version_id: str = "ver-1",
    workspace_id_in_payload: str = "ws-1",
    document_title: str = "HR Policy",
    section_path: tuple[str, ...] = ("HR", "Leave"),
    chunk_text: str = "Employees are entitled to 20 days of annual leave.",
    score: float = 0.91,
    category: str | None = "HR",
    language: str | None = "pl",
    chunk_index: int = 5,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        chunk_text=chunk_text,
        document_id=document_id,
        document_version_id=document_version_id,
        document_title=document_title,
        section_path=section_path,
        score=score,
        category=category,
        language=language,
        is_active=True,
        payload={"workspace_id": workspace_id_in_payload, "chunk_index": chunk_index},
    )


# ── CitationDTO validation ──────────────────────────────────────────────────

def test_citation_dto_is_frozen() -> None:
    svc = CitationService()
    chunks = (make_chunk(),)
    dtos = svc.build_retrieved_sources("ws-1", chunks)
    assert len(dtos) == 1
    dto = dtos[0]
    with pytest.raises((AttributeError, TypeError)):
        dto.rank = 99  # type: ignore[misc]


# ── excerpt truncation ──────────────────────────────────────────────────────

def test_excerpt_truncation_at_word_boundary() -> None:
    long_text = "word " * 100  # 500 chars
    svc = CitationService(excerpt_max_chars=20)
    chunks = (make_chunk(chunk_text=long_text),)
    dtos = svc.build_retrieved_sources("ws-1", chunks)
    excerpt = dtos[0].excerpt
    assert len(excerpt) <= 25  # some leeway for ellipsis
    assert excerpt.endswith("…")


def test_excerpt_not_truncated_when_short_enough() -> None:
    text = "Short text."
    svc = CitationService(excerpt_max_chars=300)
    chunks = (make_chunk(chunk_text=text),)
    dtos = svc.build_retrieved_sources("ws-1", chunks)
    assert dtos[0].excerpt == text


# ── deduplication by chunk_id ───────────────────────────────────────────────

def test_cited_sources_deduplicates_by_chunk_id() -> None:
    chunk_a = make_chunk(chunk_id="dup", score=0.9)
    chunk_b = make_chunk(chunk_id="dup", score=0.8)  # duplicate
    chunk_c = make_chunk(chunk_id="unique", score=0.7)

    svc = CitationService(max_exposed_citations=5)
    cited = svc.select_cited_sources("ws-1", [chunk_a, chunk_b, chunk_c])

    chunk_ids = [d.chunk_id for d in cited]
    assert chunk_ids.count("dup") == 1
    assert "unique" in chunk_ids


def test_cited_sources_respects_max_exposed() -> None:
    chunks = [make_chunk(chunk_id=f"c{i}", score=1.0 - i * 0.05) for i in range(10)]
    svc = CitationService(max_exposed_citations=3)
    cited = svc.select_cited_sources("ws-1", chunks)
    assert len(cited) == 3


# ── rank order preservation ──────────────────────────────────────────────────

def test_retrieved_sources_preserves_input_order() -> None:
    chunks = [make_chunk(chunk_id=f"c{i}", score=1.0 - i * 0.1) for i in range(4)]
    svc = CitationService()
    retrieved = svc.build_retrieved_sources("ws-1", chunks)
    assert [d.chunk_id for d in retrieved] == ["c0", "c1", "c2", "c3"]
    assert [d.rank for d in retrieved] == [1, 2, 3, 4]


# ── workspace_id propagation ────────────────────────────────────────────────

def test_retrieved_sources_workspace_id_matches_input() -> None:
    svc = CitationService()
    chunks = (make_chunk(chunk_id="c1"),)
    dtos = svc.build_retrieved_sources("my-workspace", chunks)
    assert all(d.workspace_id == "my-workspace" for d in dtos)


# ── heading extraction from section_path ────────────────────────────────────

def test_heading_extracted_from_last_section_path_element() -> None:
    svc = CitationService()
    chunks = (make_chunk(section_path=("Root", "Chapter", "Section A")),)
    dtos = svc.build_retrieved_sources("ws-1", chunks)
    assert dtos[0].heading == "Section A"


def test_heading_is_none_when_section_path_empty() -> None:
    svc = CitationService()
    chunks = (make_chunk(section_path=()),)
    dtos = svc.build_retrieved_sources("ws-1", chunks)
    assert dtos[0].heading is None


# ── empty input ──────────────────────────────────────────────────────────────

def test_build_retrieved_sources_empty_input() -> None:
    svc = CitationService()
    assert svc.build_retrieved_sources("ws-1", []) == []


def test_select_cited_sources_empty_input() -> None:
    svc = CitationService()
    assert svc.select_cited_sources("ws-1", []) == []

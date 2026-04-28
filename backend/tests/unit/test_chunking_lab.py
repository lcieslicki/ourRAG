"""Unit tests for chunking lab — strategy registry and table-aware chunking (A7)."""

import pytest

from app.domain.chunking.registry import (
    ChunkingStrategyMeta,
    STRATEGY_MARKDOWN_V1,
    STRATEGY_TABLE_AWARE_V1,
    get_strategy,
    list_strategies,
)
from app.domain.chunking.table_aware import TableAwareConfig, TableAwareMarkdownChunkingService
from app.domain.parsers.base import ParsedDocument


# ── Strategy registry lookup ──────────────────────────────────────────────────

def test_get_strategy_returns_correct_meta() -> None:
    meta = get_strategy("markdown_structure_v1")
    assert meta.name == "markdown_structure_v1"
    assert meta.version == "v1"
    assert meta.experimental is False


def test_get_strategy_table_aware_exists() -> None:
    meta = get_strategy("markdown_table_aware_v1")
    assert meta.name == "markdown_table_aware_v1"


def test_get_strategy_raises_on_unknown() -> None:
    with pytest.raises(ValueError, match="Unknown chunking strategy"):
        get_strategy("nonexistent_strategy_xyz")


def test_list_strategies_returns_all_registered() -> None:
    strategies = list_strategies()
    names = [s.name for s in strategies]
    assert "markdown_structure_v1" in names
    assert "markdown_structure_v2_smaller_chunks" in names
    assert "markdown_structure_v3_larger_context" in names
    assert "markdown_table_aware_v1" in names
    assert "parent_child_experimental_v1" in names


def test_baseline_strategy_not_experimental() -> None:
    meta = get_strategy("markdown_structure_v1")
    assert meta.experimental is False


def test_parent_child_strategy_is_experimental() -> None:
    meta = get_strategy("parent_child_experimental_v1")
    assert meta.experimental is True


def test_strategy_meta_is_frozen() -> None:
    meta = get_strategy("markdown_structure_v1")
    with pytest.raises((AttributeError, TypeError)):
        meta.name = "changed"  # type: ignore[misc]


# ── Strategy chunk_size configs ───────────────────────────────────────────────

def test_smaller_chunks_strategy_has_smaller_default_size() -> None:
    v1 = get_strategy("markdown_structure_v1")
    v2 = get_strategy("markdown_structure_v2_smaller_chunks")
    assert v2.default_chunk_size < v1.default_chunk_size


def test_larger_context_strategy_has_larger_default_size() -> None:
    v1 = get_strategy("markdown_structure_v1")
    v3 = get_strategy("markdown_structure_v3_larger_context")
    assert v3.default_chunk_size > v1.default_chunk_size


# ── TableAwareMarkdownChunkingService deterministic output ────────────────────

def _make_parsed_doc_with_table() -> ParsedDocument:
    """Create a minimal ParsedDocument containing a markdown table."""
    from app.domain.parsers.base import ParsedBlock

    table_text = (
        "| Typ | Koszt | Finansowanie |\n"
        "|-----|-------|-------------|\n"
        "| Obowiązkowe | 100% | Firma |\n"
        "| Dobrowolne | 50% | Firma |\n"
        "| Zewnętrzne | Ryczałt | Pracownik |"
    )

    full_text = "## Training Costs\n\n" + table_text

    return ParsedDocument(
        normalized_text=full_text,
        blocks=(
            ParsedBlock(kind="heading", text="## Training Costs", heading="Training Costs", section_path=("Training Costs",)),
            ParsedBlock(kind="paragraph", text=table_text, heading="Training Costs", section_path=("Training Costs",)),
        ),
        parser_name="markdown",
        parser_version="v1",
    )


def test_table_aware_service_produces_chunks() -> None:
    svc = TableAwareMarkdownChunkingService(TableAwareConfig(max_rows_per_chunk=10))
    doc = _make_parsed_doc_with_table()
    chunks = svc.chunk(doc, workspace_id="ws-1", document_version_id="v1", language="pl")
    assert len(chunks) >= 1


def test_table_aware_chunks_include_header_row() -> None:
    """Every table chunk should contain the header line."""
    svc = TableAwareMarkdownChunkingService(
        TableAwareConfig(max_rows_per_chunk=1, repeat_header_in_row_chunks=True)
    )
    doc = _make_parsed_doc_with_table()
    chunks = svc.chunk(doc, workspace_id="ws-1", document_version_id="v1", language="pl")

    # At least one chunk should reference the table header
    table_chunks = [c for c in chunks if "Typ" in c.text or "Koszt" in c.text]
    assert len(table_chunks) >= 1
    # All table chunks should repeat the header
    for tc in table_chunks:
        assert "Typ" in tc.text


def test_table_aware_chunks_have_correct_strategy_version() -> None:
    svc = TableAwareMarkdownChunkingService()
    doc = _make_parsed_doc_with_table()
    chunks = svc.chunk(doc, workspace_id="ws-1", document_version_id="v1", language="pl")
    assert all(c.chunking_strategy_version == "markdown_table_aware_v1" for c in chunks)


def test_table_aware_chunks_are_deterministic() -> None:
    """Same input always produces identical output."""
    svc = TableAwareMarkdownChunkingService(TableAwareConfig(max_rows_per_chunk=2))
    doc = _make_parsed_doc_with_table()
    run1 = svc.chunk(doc, workspace_id="ws-1", document_version_id="v1", language="pl")
    run2 = svc.chunk(doc, workspace_id="ws-1", document_version_id="v1", language="pl")
    assert [c.text for c in run1] == [c.text for c in run2]


def test_table_aware_max_rows_per_chunk_splits_table() -> None:
    """With max_rows_per_chunk=1, a 3-row table should produce 3 table chunks."""
    svc = TableAwareMarkdownChunkingService(TableAwareConfig(max_rows_per_chunk=1))
    doc = _make_parsed_doc_with_table()
    chunks = svc.chunk(doc, workspace_id="ws-1", document_version_id="v1", language="pl")
    # Should have at least 3 table-type chunks
    table_chunks = [c for c in chunks if c.metadata.get("chunk_type") == "table_row"]
    assert len(table_chunks) >= 3

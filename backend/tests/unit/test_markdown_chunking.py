import pytest

from app.domain.chunking import ChunkingConfig, MarkdownChunkingService
from app.domain.parsers import MarkdownParser


def fixture_bytes(name: str) -> bytes:
    return (pytest.FIXTURES_DIR / "markdown" / name).read_bytes()


def parse_markdown(markdown: bytes):
    return MarkdownParser().parse(markdown)


def test_chunking_preserves_workspace_version_language_and_strategy_metadata() -> None:
    parsed = parse_markdown(b"# HR\n\nVacation policy details.\n")
    service = MarkdownChunkingService(ChunkingConfig(chunk_size=120, chunk_overlap=10, strategy_version="test_v1"))

    chunks = service.chunk(
        parsed,
        workspace_id="workspace-1",
        document_version_id="version-1",
        language="pl",
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].workspace_id == "workspace-1"
    assert chunks[0].document_version_id == "version-1"
    assert chunks[0].language == "pl"
    assert chunks[0].chunking_strategy_version == "test_v1"
    assert chunks[0].heading == "HR"
    assert chunks[0].section_path == ("HR",)


def test_chunking_prefers_heading_boundaries() -> None:
    parsed = parse_markdown(b"# HR\n\nVacation policy.\n\n# IT\n\nPassword policy.\n")
    service = MarkdownChunkingService(ChunkingConfig(chunk_size=80, chunk_overlap=0))

    chunks = service.chunk(parsed, workspace_id="workspace-1", document_version_id="version-1", language="pl")

    assert [chunk.heading for chunk in chunks] == ["HR", "IT"]
    assert chunks[0].text == "# HR\n\nVacation policy."
    assert chunks[1].text == "# IT\n\nPassword policy."


def test_chunking_splits_large_sections_on_semantic_parts_before_hard_split() -> None:
    parsed = parse_markdown(
        b"# HR\n\nFirst paragraph has useful context.\n\nSecond paragraph has separate context.\n\nThird paragraph closes it.\n"
    )
    service = MarkdownChunkingService(ChunkingConfig(chunk_size=75, chunk_overlap=0))

    chunks = service.chunk(parsed, workspace_id="workspace-1", document_version_id="version-1", language="pl")

    assert [chunk.chunk_index for chunk in chunks] == [0, 1]
    assert chunks[0].section_path == ("HR",)
    assert chunks[1].section_path == ("HR",)
    assert "First paragraph" in chunks[0].text
    assert "Third paragraph" in chunks[1].text


def test_chunking_applies_configured_overlap_between_chunks() -> None:
    parsed = parse_markdown(b"# HR\n\nAlpha paragraph.\n\nBeta paragraph.\n\nGamma paragraph.\n")
    service = MarkdownChunkingService(ChunkingConfig(chunk_size=45, chunk_overlap=8))

    chunks = service.chunk(parsed, workspace_id="workspace-1", document_version_id="version-1", language="pl")

    assert len(chunks) > 1
    assert chunks[1].text.startswith(chunks[0].text[-8:].strip())


def test_chunking_hard_splits_single_oversized_part_deterministically() -> None:
    parsed = parse_markdown(("# HR\n\n" + "A" * 130 + "\n").encode())
    service = MarkdownChunkingService(ChunkingConfig(chunk_size=50, chunk_overlap=0))

    chunks = service.chunk(parsed, workspace_id="workspace-1", document_version_id="version-1", language="pl")

    assert [chunk.chunk_index for chunk in chunks] == [0, 1, 2]
    assert all(len(chunk.text) <= 50 for chunk in chunks)
    assert all(chunk.section_path == ("HR",) for chunk in chunks)


def test_chunking_config_rejects_invalid_overlap() -> None:
    with pytest.raises(ValueError):
        ChunkingConfig(chunk_size=100, chunk_overlap=100)


def test_chunking_preserves_semantic_order_from_fixture() -> None:
    parsed = parse_markdown(fixture_bytes("chunk_order.md"))
    service = MarkdownChunkingService(ChunkingConfig(chunk_size=65, chunk_overlap=0))

    chunks = service.chunk(parsed, workspace_id="workspace-1", document_version_id="version-1", language="pl")

    chunk_text = "\n".join(chunk.text for chunk in chunks)
    assert chunk_text.index("Alpha first paragraph.") < chunk_text.index("Alpha second paragraph.")
    assert chunk_text.index("Alpha second paragraph.") < chunk_text.index("Beta first paragraph.")
    assert chunk_text.index("Beta second paragraph.") < chunk_text.index("Gamma final paragraph.")
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))


def test_chunking_generates_section_paths_from_nested_headings() -> None:
    parsed = parse_markdown(fixture_bytes("policy.md"))
    service = MarkdownChunkingService(ChunkingConfig(chunk_size=90, chunk_overlap=0))

    chunks = service.chunk(parsed, workspace_id="workspace-1", document_version_id="version-1", language="pl")

    assert ("HR",) in [chunk.section_path for chunk in chunks]
    assert ("HR", "Approval") in [chunk.section_path for chunk in chunks]
    assert ("HR", "Approval", "Emergency Leave") in [chunk.section_path for chunk in chunks]
    assert ("IT",) in [chunk.section_path for chunk in chunks]


def test_chunking_output_is_deterministic_for_same_input_and_config() -> None:
    parsed = parse_markdown(fixture_bytes("policy.md"))
    service = MarkdownChunkingService(ChunkingConfig(chunk_size=75, chunk_overlap=12, strategy_version="test_v1"))

    first = service.chunk(parsed, workspace_id="workspace-1", document_version_id="version-1", language="pl")
    second = service.chunk(parsed, workspace_id="workspace-1", document_version_id="version-1", language="pl")

    assert first == second

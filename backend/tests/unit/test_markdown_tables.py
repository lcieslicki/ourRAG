from app.domain.chunking.markdown import ChunkingConfig, MarkdownChunkingService
from app.domain.chunking.tables import detect_markdown_tables, parse_markdown_table
from app.domain.parsers import MarkdownParser


def parse_markdown(markdown: str):
    return MarkdownParser().parse(markdown.encode("utf-8"))


def table_markdown() -> str:
    return """## 2. Rodzaje szkoleń

| Typ | Opis | Finansowanie |
|---|---|---|
| Obowiązkowe | BHP, ppoż., uprawnienia (np. wózki widłowe, elektryczne) | 100% firma |
| Rozwojowe | Zgodne z IDP pracownika, zatwierdzone przez przełożonego | Do 80% firma |
"""


def chunk(markdown: str):
    return MarkdownChunkingService(ChunkingConfig(chunk_size=1200, chunk_overlap=0)).chunk(
        parse_markdown(markdown),
        workspace_id="workspace-1",
        document_version_id="version-1",
        language="pl",
        document_id="document-1",
        document_name="Training procedure",
    )


def test_detects_simple_valid_markdown_table() -> None:
    matches = detect_markdown_tables(table_markdown())

    assert len(matches) == 1
    assert matches[0].lines[0] == "| Typ | Opis | Finansowanie |"


def test_parses_table_headers_and_rows_with_polish_content() -> None:
    table = parse_markdown_table(detect_markdown_tables(table_markdown())[0].lines)

    assert table is not None
    assert table.headers == ("Typ", "Opis", "Finansowanie")
    assert table.rows[1] == (
        "Rozwojowe",
        "Zgodne z IDP pracownika, zatwierdzone przez przełożonego",
        "Do 80% firma",
    )


def test_ignores_malformed_table_row_without_breaking_valid_rows() -> None:
    markdown = """## Dane

| Typ | Opis | Finansowanie |
|---|---|---|
| Poprawny | Opis | 100% |
| Zły | Za mało |
| Drugi poprawny | Opis drugi | 80% |
"""

    table = parse_markdown_table(detect_markdown_tables(markdown)[0].lines)

    assert table is not None
    assert [row[0] for row in table.rows] == ["Poprawny", "Drugi poprawny"]


def test_chunking_generates_overview_and_row_chunks_with_section_heading() -> None:
    chunks = chunk(table_markdown())

    assert [item.metadata["chunk_type"] for item in chunks] == [
        "table_overview",
        "table_row",
        "table_row",
    ]
    assert chunks[0].heading == "2. Rodzaje szkoleń"
    assert "This table contains 2 rows:" in chunks[0].text
    assert "- Rozwojowe" in chunks[0].text
    assert "Document: Training procedure" in chunks[1].text
    assert "Section: 2. Rodzaje szkoleń" in chunks[1].text


def test_row_chunk_uses_label_value_text_instead_of_raw_markdown() -> None:
    chunks = chunk(table_markdown())
    row = next(item for item in chunks if item.metadata.get("row_key") == "rozwojowe")

    assert "| Rozwojowe |" not in row.text
    assert "Typ: Rozwojowe." in row.text
    assert "Opis: Zgodne z IDP pracownika, zatwierdzone przez przełożonego." in row.text
    assert "Finansowanie: Do 80% firma." in row.text


def test_table_chunk_metadata_contains_table_name_row_key_and_json() -> None:
    chunks = chunk(table_markdown())
    row = next(item for item in chunks if item.metadata.get("chunk_type") == "table_row")

    assert row.metadata["document_id"] == "document-1"
    assert row.metadata["document_name"] == "Training procedure"
    assert row.metadata["section"] == "2. Rodzaje szkoleń"
    assert row.metadata["table_name"] == "2_rodzaje_szkolen"
    assert row.metadata["row_key"] == "obowiazkowe"
    assert row.metadata["source_format"] == "markdown_table"
    assert row.metadata["table_json"]["headers"] == ["Typ", "Opis", "Finansowanie"]


def test_section_with_prose_and_table_preserves_both() -> None:
    chunks = chunk(
        """## Szkolenia

Przed tabelą jest kontekst procedury.

| Typ | Opis |
|---|---|
| BHP | Szkolenie obowiązkowe |

Po tabeli jest informacja końcowa.
"""
    )

    chunk_types = [item.metadata["chunk_type"] for item in chunks]

    assert chunk_types == ["prose", "table_overview", "table_row", "prose"]
    assert "Przed tabelą jest kontekst procedury." in chunks[0].text
    assert "Po tabeli jest informacja końcowa." in chunks[-1].text
    assert all("|---|" not in item.text for item in chunks)

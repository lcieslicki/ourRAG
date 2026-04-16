import pytest

from app.domain.parsers import MarkdownParser, ParserRegistry


def test_markdown_parser_normalizes_line_endings_and_preserves_headings() -> None:
    parser = MarkdownParser()

    parsed = parser.parse(b"# HR\r\n\r\nVacation policy\r\n\r\n## Approval\r\nAsk your manager.\r\n")

    assert parsed.parser_name == "markdown"
    assert parsed.parser_version == "markdown_parser_v1"
    assert parsed.normalized_text == "# HR\n\nVacation policy\n\n## Approval\nAsk your manager.\n"
    assert [block.kind for block in parsed.blocks] == ["heading", "paragraph", "heading", "paragraph"]
    assert parsed.blocks[0].heading == "HR"
    assert parsed.blocks[0].section_path == ("HR",)
    assert parsed.blocks[2].section_path == ("HR", "Approval")
    assert parsed.blocks[3].text == "Ask your manager."


def test_markdown_parser_preserves_lists_as_structural_blocks() -> None:
    parsed = MarkdownParser().parse(
        b"# Onboarding\n\n- Create account\n- Assign laptop\n\nNext step.\n"
    )

    assert [block.kind for block in parsed.blocks] == ["heading", "list", "paragraph"]
    assert parsed.blocks[1].text == "- Create account\n- Assign laptop"
    assert parsed.blocks[1].section_path == ("Onboarding",)
    assert parsed.blocks[2].text == "Next step."


def test_markdown_parser_collapses_excess_blank_lines_without_merging_sections() -> None:
    parsed = MarkdownParser().parse(b"# A\n\n\n\nText\n\n\n## B\n\nMore\n")

    assert parsed.normalized_text == "# A\n\n\nText\n\n\n## B\n\nMore\n"
    assert [block.kind for block in parsed.blocks] == ["heading", "paragraph", "heading", "paragraph"]
    assert parsed.blocks[3].section_path == ("A", "B")


def test_markdown_parser_preserves_code_fences_as_code_blocks() -> None:
    parsed = MarkdownParser().parse(b"# API\n\n```json\n{\"ok\": true}\n```\n\nDone.\n")

    assert [block.kind for block in parsed.blocks] == ["heading", "code", "paragraph"]
    assert parsed.blocks[1].text == '```json\n{"ok": true}\n```'
    assert parsed.blocks[1].section_path == ("API",)


def test_parser_registry_selects_parser_by_extension() -> None:
    registry = ParserRegistry([MarkdownParser()])

    assert isinstance(registry.get("md"), MarkdownParser)
    assert isinstance(registry.get(".markdown"), MarkdownParser)


def test_parser_registry_rejects_unregistered_extensions() -> None:
    registry = ParserRegistry([MarkdownParser()])

    with pytest.raises(ValueError):
        registry.get(".pdf")

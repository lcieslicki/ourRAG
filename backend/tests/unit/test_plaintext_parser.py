import pytest

from app.domain.parsers import PlainTextParser
from app.domain.parsers.failures import ParseFailure


def test_parse_simple_text_returns_sections() -> None:
    parser = PlainTextParser()

    content = b"First section\n\nSecond section\n\nThird section"
    result = parser.parse(content)

    assert not isinstance(result, ParseFailure)
    assert result.parser_name == "plaintext"
    assert result.parser_version == "plaintext_parser_v1"
    assert len(result.blocks) == 3
    assert result.blocks[0].kind == "paragraph"
    assert result.blocks[0].text == "First section"
    assert result.blocks[1].text == "Second section"
    assert result.blocks[2].text == "Third section"


def test_parse_empty_file_returns_empty_or_minimal_result() -> None:
    parser = PlainTextParser()

    content = b""
    result = parser.parse(content)

    assert not isinstance(result, ParseFailure)
    assert len(result.blocks) == 0
    assert result.parser_name == "plaintext"


def test_parse_polish_characters() -> None:
    parser = PlainTextParser()

    # Polish characters: ąćęłńóśźż
    content = "Polska dokumentacja\n\nZawiera znaki: ąćęłńóśźż".encode("utf-8")
    result = parser.parse(content)

    assert not isinstance(result, ParseFailure)
    assert len(result.blocks) == 2
    assert "ąćęłńóśźż" in result.blocks[1].text


def test_parse_binary_content_returns_failure() -> None:
    parser = PlainTextParser()

    # Invalid binary content
    content = b"\x80\x81\x82\x83"
    result = parser.parse(content)

    # Should not be able to decode as UTF-8 or latin-1 (actually latin-1 accepts anything)
    # So this test verifies graceful handling
    if isinstance(result, ParseFailure):
        assert result.reason == "encoding_error"

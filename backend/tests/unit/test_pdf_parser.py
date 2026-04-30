import pytest

from app.domain.parsers.pdf import PdfParser
from app.domain.parsers.failures import ParseFailure


def test_parse_corrupt_bytes_returns_failure() -> None:
    parser = PdfParser()

    # Invalid PDF content
    content = b"not a pdf"
    result = parser.parse(content)

    assert isinstance(result, ParseFailure)
    assert result.reason == "corrupt"


def test_parse_empty_bytes_returns_failure() -> None:
    parser = PdfParser()

    content = b""
    result = parser.parse(content)

    assert isinstance(result, ParseFailure)
    assert result.reason == "corrupt"


def test_pdf_parser_handles_import_error_gracefully() -> None:
    """Test that missing pypdf dependency raises informative error."""
    parser = PdfParser()

    # Simulate import error by setting the internal flag
    parser._import_error = ImportError("No module named 'pypdf'")

    content = b"some content"

    with pytest.raises(ImportError) as exc_info:
        parser.parse(content)

    assert "pypdf is required" in str(exc_info.value)
    assert "pip install pypdf" in str(exc_info.value)

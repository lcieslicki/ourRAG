from typing import TYPE_CHECKING

from app.domain.parsers.base import normalize_extension

if TYPE_CHECKING:
    from app.core.config.parser_config import ParserConfig


class ParserRegistry:
    """
    Registry mapping file extensions to parser instances.
    """

    def __init__(self) -> None:
        self._parsers_by_extension: dict[str, object] = {}

    def register(self, ext: str, parser_class: type) -> None:
        """
        Register a parser class for a given file extension.

        Args:
            ext: File extension (e.g., ".md" or "md")
            parser_class: Parser class to instantiate
        """
        normalized_ext = normalize_extension(ext)
        self._parsers_by_extension[normalized_ext] = parser_class()

    def get_parser(self, filename: str) -> object | None:
        """
        Get a parser for the given filename, or None if unsupported.

        Args:
            filename: Filename with extension (e.g., "document.pdf")

        Returns:
            Parser instance or None
        """
        if not filename:
            return None

        # Extract extension
        if "." not in filename:
            return None

        ext = "." + filename.rsplit(".", 1)[-1]
        normalized_ext = normalize_extension(ext)

        return self._parsers_by_extension.get(normalized_ext)


def create_default_registry(config: "ParserConfig") -> ParserRegistry:
    """
    Create a default ParserRegistry with parsers enabled per config.

    Args:
        config: ParserConfig instance

    Returns:
        Configured ParserRegistry
    """
    registry = ParserRegistry()

    # Always register Markdown
    from app.domain.parsers.markdown import MarkdownParser

    registry.register(".md", MarkdownParser)

    # Always register PlainText
    from app.domain.parsers.plaintext import PlainTextParser

    registry.register(".txt", PlainTextParser)

    # Register PDF if enabled
    if config.parser_pdf_enabled:
        from app.domain.parsers.pdf import PdfParser

        registry.register(".pdf", PdfParser)

    # Register DOCX if enabled
    if config.parser_docx_enabled:
        from app.domain.parsers.docx import DocxParser

        registry.register(".docx", DocxParser)

    return registry

from app.domain.parsers.base import ParsedBlock, ParsedDocument
from app.domain.parsers.failures import ParseFailure


class PlainTextParser:
    supported_extensions = (".txt",)
    parser_name = "plaintext"
    parser_version = "plaintext_parser_v1"

    def parse(self, content: bytes) -> ParsedDocument | ParseFailure:
        """
        Parse plain text content, splitting on double newlines to create sections.
        Tries UTF-8 first, then falls back to latin-1 encoding.
        """
        # Try UTF-8 first
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            # Fall back to latin-1
            try:
                text = content.decode("latin-1")
            except Exception as e:
                return ParseFailure(
                    filename="",
                    reason="encoding_error",
                    error_message=f"Could not decode file with UTF-8 or latin-1: {str(e)}",
                )

        normalized_text = normalize_plaintext(text)
        blocks = tuple(parse_blocks(normalized_text))

        return ParsedDocument(
            normalized_text=normalized_text,
            blocks=blocks,
            parser_name=self.parser_name,
            parser_version=self.parser_version,
        )


def normalize_plaintext(text: str) -> str:
    """Normalize line endings and preserve structure."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in normalized.split("\n")]
    collapsed: list[str] = []
    blank_count = 0

    for line in lines:
        if line.strip() == "":
            blank_count += 1
            if blank_count <= 2:
                collapsed.append("")
            continue

        blank_count = 0
        collapsed.append(line)

    return "\n".join(collapsed).strip() + "\n"


def parse_blocks(text: str) -> list[ParsedBlock]:
    """
    Parse plaintext into blocks using double newlines as section boundaries.
    """
    blocks: list[ParsedBlock] = []

    # Split by double newlines to identify logical sections
    sections = text.split("\n\n")

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Create a block for this section
        blocks.append(
            ParsedBlock(
                kind="paragraph",
                text=section,
                section_path=(),
            )
        )

    return blocks

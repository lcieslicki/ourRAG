# Requires: pypdf
# Install with: pip install pypdf

import io
import re
from typing import TYPE_CHECKING

from app.domain.parsers.base import ParsedBlock, ParsedDocument
from app.domain.parsers.failures import ParseFailure

if TYPE_CHECKING:
    import pypdf


class PdfParser:
    supported_extensions = (".pdf",)
    parser_name = "pdf"
    parser_version = "pdf_parser_v1"

    def __init__(self) -> None:
        """Initialize the PDF parser, checking for required dependencies."""
        try:
            import pypdf  # noqa: F401
        except ImportError as e:
            self._import_error = e
        else:
            self._import_error = None

    def parse(self, content: bytes) -> ParsedDocument | ParseFailure:
        """
        Extract text from PDF page by page.
        Creates one section per page, detects headings heuristically.
        Preserves page numbers in metadata.
        """
        if self._import_error:
            raise ImportError(
                "pypdf is required to parse PDF files. "
                "Install with: pip install pypdf"
            ) from self._import_error

        import pypdf

        try:
            pdf_reader = pypdf.PdfReader(io.BytesIO(content))
        except Exception as e:
            error_msg = str(e).lower()
            if "encrypted" in error_msg or "password" in error_msg:
                return ParseFailure(
                    filename="",
                    reason="encrypted",
                    error_message="PDF is password-protected",
                )
            elif "corrupt" in error_msg or "invalid" in error_msg:
                return ParseFailure(
                    filename="",
                    reason="corrupt",
                    error_message=f"PDF is corrupted: {str(e)}",
                )
            else:
                return ParseFailure(
                    filename="",
                    reason="corrupt",
                    error_message=f"Failed to parse PDF: {str(e)}",
                )

        if len(pdf_reader.pages) == 0:
            return ParseFailure(
                filename="",
                reason="empty",
                error_message="PDF has no pages",
            )

        blocks: list[ParsedBlock] = []
        normalized_lines: list[str] = []

        for page_num, page in enumerate(pdf_reader.pages, start=1):
            try:
                text = page.extract_text()
            except Exception as e:
                # Skip pages that fail to extract
                continue

            if not text or not text.strip():
                continue

            # Normalize line endings
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            lines = text.split("\n")

            page_blocks = _parse_page_blocks(lines, page_num)
            blocks.extend(page_blocks)
            normalized_lines.extend(lines)

        normalized_text = "\n".join(normalized_lines)
        if normalized_text:
            normalized_text += "\n"

        return ParsedDocument(
            normalized_text=normalized_text,
            blocks=tuple(blocks),
            parser_name=self.parser_name,
            parser_version=self.parser_version,
        )


def _parse_page_blocks(lines: list[str], page_num: int) -> list[ParsedBlock]:
    """
    Parse lines from a PDF page into blocks.
    Detects headings: ALL CAPS lines or numbered/bullet patterns.
    """
    blocks: list[ParsedBlock] = []
    current_section: str | None = None
    paragraph_lines: list[str] = []
    heading_re = re.compile(r"^\d+[\.\)]\s+")  # Numbered list: "1. " or "1) "

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if paragraph_lines:
            text = "\n".join(paragraph_lines).strip()
            if text:
                section_path = (current_section,) if current_section else ()
                blocks.append(
                    ParsedBlock(
                        kind="paragraph",
                        text=text,
                        section_path=section_path,
                    )
                )
            paragraph_lines = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            continue

        # Check if line is a heading (ALL CAPS or numbered)
        is_all_caps = (
            stripped.isupper()
            and len(stripped) > 3
            and any(c.isalpha() for c in stripped)
        )
        is_numbered = heading_re.match(stripped)

        if is_all_caps or is_numbered:
            flush_paragraph()
            current_section = stripped
            blocks.append(
                ParsedBlock(
                    kind="heading",
                    text=line,
                    section_path=(current_section,),
                    heading=current_section,
                    level=1,
                )
            )
        else:
            paragraph_lines.append(line)

    flush_paragraph()
    return blocks

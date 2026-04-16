import re

from app.domain.parsers.base import ParsedBlock, ParsedDocument

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
LIST_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")


class MarkdownParser:
    supported_extensions = (".md", ".markdown")
    parser_name = "markdown"
    parser_version = "markdown_parser_v1"

    def parse(self, content: bytes) -> ParsedDocument:
        text = content.decode("utf-8-sig")
        normalized_text = normalize_markdown_text(text)
        blocks = tuple(parse_blocks(normalized_text))

        return ParsedDocument(
            normalized_text=normalized_text,
            blocks=blocks,
            parser_name=self.parser_name,
            parser_version=self.parser_version,
        )


def normalize_markdown_text(text: str) -> str:
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
    blocks: list[ParsedBlock] = []
    section_stack: list[tuple[int, str]] = []
    paragraph_lines: list[str] = []
    list_lines: list[str] = []
    code_lines: list[str] = []
    in_code_fence = False

    def current_section_path() -> tuple[str, ...]:
        return tuple(heading for _, heading in section_stack)

    def flush_paragraph() -> None:
        if paragraph_lines:
            blocks.append(
                ParsedBlock(
                    kind="paragraph",
                    text="\n".join(paragraph_lines).strip(),
                    section_path=current_section_path(),
                )
            )
            paragraph_lines.clear()

    def flush_list() -> None:
        if list_lines:
            blocks.append(
                ParsedBlock(
                    kind="list",
                    text="\n".join(list_lines).strip(),
                    section_path=current_section_path(),
                )
            )
            list_lines.clear()

    def flush_code() -> None:
        if code_lines:
            blocks.append(
                ParsedBlock(
                    kind="code",
                    text="\n".join(code_lines).strip(),
                    section_path=current_section_path(),
                )
            )
            code_lines.clear()

    for line in text.split("\n"):
        if line.startswith("```"):
            flush_paragraph()
            flush_list()
            code_lines.append(line)
            in_code_fence = not in_code_fence

            if not in_code_fence:
                flush_code()

            continue

        if in_code_fence:
            code_lines.append(line)
            continue

        heading_match = HEADING_RE.match(line)

        if heading_match:
            flush_paragraph()
            flush_list()
            level = len(heading_match.group(1))
            heading = heading_match.group(2).strip()
            section_stack[:] = [(existing_level, value) for existing_level, value in section_stack if existing_level < level]
            section_stack.append((level, heading))
            blocks.append(
                ParsedBlock(
                    kind="heading",
                    text=line.strip(),
                    section_path=current_section_path(),
                    heading=heading,
                    level=level,
                )
            )
            continue

        if line.strip() == "":
            flush_paragraph()
            flush_list()
            continue

        if LIST_RE.match(line):
            flush_paragraph()
            list_lines.append(line)
            continue

        flush_list()
        paragraph_lines.append(line)

    flush_paragraph()
    flush_list()
    flush_code()
    return blocks

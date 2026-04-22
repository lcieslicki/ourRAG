from dataclasses import dataclass
import re
import unicodedata
from typing import Any


@dataclass(frozen=True)
class MarkdownTableMatch:
    start_line: int
    end_line: int
    lines: tuple[str, ...]


@dataclass(frozen=True)
class MarkdownTable:
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    raw_lines: tuple[str, ...]

    def as_json(self) -> dict[str, Any]:
        return {
            "headers": list(self.headers),
            "rows": [dict(zip(self.headers, row, strict=True)) for row in self.rows],
        }


@dataclass(frozen=True)
class TableChunk:
    text: str
    metadata: dict[str, Any]


def detect_markdown_tables(text: str) -> tuple[MarkdownTableMatch, ...]:
    lines = text.splitlines()
    matches: list[MarkdownTableMatch] = []
    index = 0

    while index < len(lines) - 1:
        if not is_pipe_row(lines[index]) or not is_separator_row(lines[index + 1]):
            index += 1
            continue

        start = index
        end = index + 2

        while end < len(lines) and is_pipe_row(lines[end]):
            end += 1

        matches.append(
            MarkdownTableMatch(
                start_line=start,
                end_line=end,
                lines=tuple(lines[start:end]),
            )
        )
        index = end

    return tuple(matches)


def parse_markdown_table(lines: tuple[str, ...] | list[str]) -> MarkdownTable | None:
    if len(lines) < 2:
        return None

    headers = split_pipe_row(lines[0])
    if not headers or not is_separator_row(lines[1]):
        return None

    rows: list[tuple[str, ...]] = []
    for line in lines[2:]:
        values = split_pipe_row(line)
        normalized = normalize_row(values, width=len(headers))
        if normalized is not None:
            rows.append(normalized)

    if not rows:
        return None

    return normalize_table(MarkdownTable(headers=tuple(headers), rows=tuple(rows), raw_lines=tuple(lines)))


def normalize_table(table: MarkdownTable) -> MarkdownTable | None:
    headers = tuple(header.strip() for header in table.headers if header.strip())
    if not headers:
        return None

    rows: list[tuple[str, ...]] = []
    for row in table.rows:
        normalized = normalize_row(list(row), width=len(headers))
        if normalized is not None and any(cell.strip() for cell in normalized):
            rows.append(normalized)

    if not rows:
        return None

    return MarkdownTable(headers=headers, rows=tuple(rows), raw_lines=table.raw_lines)


def generate_table_overview_chunk(
    table: MarkdownTable,
    *,
    document_id: str | None,
    document_name: str | None,
    section: str | None,
    section_path: tuple[str, ...],
) -> TableChunk:
    lines = common_context_lines(document_name=document_name, section=section)
    lines.append(f"This table contains {len(table.rows)} rows:")

    for row in table.rows:
        primary = first_meaningful_cell(row) or "Row"
        details = labeled_values(table.headers[1:], row[1:])
        suffix = f" — {details}" if details else ""
        lines.append(f"- {primary}{suffix}")

    metadata = build_chunk_metadata(
        chunk_type="table_overview",
        table=table,
        row=None,
        document_id=document_id,
        document_name=document_name,
        section=section,
        section_path=section_path,
    )
    return TableChunk(text="\n".join(lines).strip(), metadata=metadata)


def generate_table_row_chunks(
    table: MarkdownTable,
    *,
    document_id: str | None,
    document_name: str | None,
    section: str | None,
    section_path: tuple[str, ...],
) -> tuple[TableChunk, ...]:
    chunks: list[TableChunk] = []

    for row in table.rows:
        lines = common_context_lines(document_name=document_name, section=section)
        lines.extend(f"{header}: {value}." for header, value in zip(table.headers, row, strict=True) if value)
        chunks.append(
            TableChunk(
                text="\n".join(lines).strip(),
                metadata=build_chunk_metadata(
                    chunk_type="table_row",
                    table=table,
                    row=row,
                    document_id=document_id,
                    document_name=document_name,
                    section=section,
                    section_path=section_path,
                ),
            )
        )

    return tuple(chunks)


def build_chunk_metadata(
    *,
    chunk_type: str,
    table: MarkdownTable | None,
    row: tuple[str, ...] | None,
    document_id: str | None,
    document_name: str | None,
    section: str | None,
    section_path: tuple[str, ...],
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "chunk_type": chunk_type,
        "source_format": "markdown_table" if chunk_type.startswith("table_") else "markdown",
        "section": section,
        "section_path": list(section_path),
    }

    if document_id:
        metadata["document_id"] = document_id
    if document_name:
        metadata["document_name"] = document_name
    if table is not None:
        metadata["table_name"] = slugify(section or "table")
        metadata["table_json"] = table.as_json()
    if row is not None:
        metadata["row_key"] = slugify(first_meaningful_cell(row) or "row")

    return metadata


def split_text_around_tables(text: str, matches: tuple[MarkdownTableMatch, ...]) -> list[tuple[str, str | MarkdownTableMatch]]:
    if not matches:
        return [("prose", text)]

    lines = text.splitlines()
    parts: list[tuple[str, str | MarkdownTableMatch]] = []
    cursor = 0

    for match in matches:
        before = "\n".join(lines[cursor:match.start_line]).strip()
        if before:
            parts.append(("prose", before))
        parts.append(("table", match))
        cursor = match.end_line

    after = "\n".join(lines[cursor:]).strip()
    if after:
        parts.append(("prose", after))

    return parts


def is_pipe_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.count("|") >= 2 and not stripped.startswith("```")


def is_separator_row(line: str) -> bool:
    cells = split_pipe_row(line)
    if not cells:
        return False
    return all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def split_pipe_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def normalize_row(values: list[str], *, width: int) -> tuple[str, ...] | None:
    if len(values) == width:
        return tuple(value.strip() for value in values)
    if len(values) > width and all(not value.strip() for value in values[width:]):
        return tuple(value.strip() for value in values[:width])
    return None


def common_context_lines(*, document_name: str | None, section: str | None) -> list[str]:
    lines: list[str] = []
    if document_name:
        lines.append(f"Document: {document_name}")
    if section:
        lines.append(f"Section: {section}")
    if lines:
        lines.append("")
    return lines


def labeled_values(headers: tuple[str, ...], values: tuple[str, ...]) -> str:
    return "; ".join(f"{header}: {value}" for header, value in zip(headers, values, strict=True) if value)


def first_meaningful_cell(row: tuple[str, ...]) -> str | None:
    return next((cell.strip() for cell in row if cell.strip()), None)


def slugify(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^0-9A-Za-z]+", "_", ascii_value.lower()).strip("_")
    return slug or "table"

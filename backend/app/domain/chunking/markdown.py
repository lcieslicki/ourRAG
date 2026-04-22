from dataclasses import dataclass, field

from app.domain.chunking.tables import (
    MarkdownTableMatch,
    build_chunk_metadata,
    detect_markdown_tables,
    generate_table_overview_chunk,
    generate_table_row_chunks,
    parse_markdown_table,
    split_text_around_tables,
)
from app.domain.parsers.base import ParsedDocument

DEFAULT_CHUNKING_STRATEGY = "markdown_semantic_v1"


@dataclass(frozen=True)
class ChunkingConfig:
    chunk_size: int
    chunk_overlap: int
    strategy_version: str = DEFAULT_CHUNKING_STRATEGY

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")

        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap must be non-negative")

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")


@dataclass(frozen=True)
class DocumentChunk:
    chunk_index: int
    text: str
    heading: str | None
    section_path: tuple[str, ...]
    document_version_id: str
    workspace_id: str
    language: str
    chunking_strategy_version: str
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ChunkCandidate:
    text: str
    heading: str | None
    section_path: tuple[str, ...]
    chunk_type: str = "prose"
    metadata: dict = field(default_factory=dict)
    apply_overlap: bool = True


class MarkdownChunkingService:
    def __init__(self, config: ChunkingConfig) -> None:
        self.config = config

    def chunk(
        self,
        parsed_document: ParsedDocument,
        *,
        workspace_id: str,
        document_version_id: str,
        language: str,
        document_id: str | None = None,
        document_name: str | None = None,
    ) -> tuple[DocumentChunk, ...]:
        chunks: list[DocumentChunk] = []
        previous_overlap_text: str | None = None

        for candidate in self._build_candidates(
            parsed_document,
            document_id=document_id,
            document_name=document_name,
        ):
            for piece in self._split_candidate(candidate):
                text = (
                    self._with_overlap(previous_overlap_text, piece.text)
                    if piece.apply_overlap
                    else piece.text
                )
                chunks.append(
                    DocumentChunk(
                        chunk_index=len(chunks),
                        text=text,
                        heading=piece.heading,
                        section_path=piece.section_path,
                        document_version_id=document_version_id,
                        workspace_id=workspace_id,
                        language=language,
                        chunking_strategy_version=self.config.strategy_version,
                        metadata={
                            **build_chunk_metadata(
                                chunk_type=piece.chunk_type,
                                table=None,
                                row=None,
                                document_id=document_id,
                                document_name=document_name,
                                section=piece.heading,
                                section_path=piece.section_path,
                            ),
                            **piece.metadata,
                        },
                    )
                )
                previous_overlap_text = text if piece.apply_overlap else None

        return tuple(chunks)

    def _build_candidates(
        self,
        parsed_document: ParsedDocument,
        *,
        document_id: str | None,
        document_name: str | None,
    ) -> list[ChunkCandidate]:
        candidates: list[ChunkCandidate] = []
        current_lines: list[str] = []
        current_section_path: tuple[str, ...] = ()
        current_heading: str | None = None

        def flush() -> None:
            if current_lines:
                candidates.extend(
                    self._candidates_from_text(
                        "\n\n".join(current_lines).strip(),
                        heading=current_heading,
                        section_path=current_section_path,
                        document_id=document_id,
                        document_name=document_name,
                    )
                )
                current_lines.clear()

        for block in parsed_document.blocks:
            if block.kind == "heading":
                flush()
                current_section_path = block.section_path
                current_heading = block.heading
                current_lines.append(block.text)
                continue

            if block.section_path != current_section_path:
                flush()
                current_section_path = block.section_path
                current_heading = block.section_path[-1] if block.section_path else None

            current_lines.append(block.text)

        flush()
        return candidates

    def _candidates_from_text(
        self,
        text: str,
        *,
        heading: str | None,
        section_path: tuple[str, ...],
        document_id: str | None,
        document_name: str | None,
    ) -> list[ChunkCandidate]:
        table_matches = detect_markdown_tables(text)
        if not table_matches:
            return [
                ChunkCandidate(
                    text=text,
                    heading=heading,
                    section_path=section_path,
                    metadata=build_chunk_metadata(
                        chunk_type="prose",
                        table=None,
                        row=None,
                        document_id=document_id,
                        document_name=document_name,
                        section=heading,
                        section_path=section_path,
                    ),
                )
            ]

        candidates: list[ChunkCandidate] = []
        for part_type, value in split_text_around_tables(text, table_matches):
            if part_type == "prose":
                prose_text = str(value).strip()
                if self._is_heading_only(prose_text, heading=heading):
                    continue
                if prose_text:
                    candidates.append(
                        ChunkCandidate(
                            text=prose_text,
                            heading=heading,
                            section_path=section_path,
                            metadata=build_chunk_metadata(
                                chunk_type="prose",
                                table=None,
                                row=None,
                                document_id=document_id,
                                document_name=document_name,
                                section=heading,
                                section_path=section_path,
                            ),
                        )
                    )
                continue

            if not isinstance(value, MarkdownTableMatch):
                continue

            table = parse_markdown_table(value.lines)
            if table is None:
                continue

            overview = generate_table_overview_chunk(
                table,
                document_id=document_id,
                document_name=document_name,
                section=heading,
                section_path=section_path,
            )
            candidates.append(
                ChunkCandidate(
                    text=overview.text,
                    heading=heading,
                    section_path=section_path,
                    chunk_type="table_overview",
                    metadata=overview.metadata,
                    apply_overlap=False,
                )
            )
            for row_chunk in generate_table_row_chunks(
                table,
                document_id=document_id,
                document_name=document_name,
                section=heading,
                section_path=section_path,
            ):
                candidates.append(
                    ChunkCandidate(
                        text=row_chunk.text,
                        heading=heading,
                        section_path=section_path,
                        chunk_type="table_row",
                        metadata=row_chunk.metadata,
                        apply_overlap=False,
                    )
                )

        return candidates

    @staticmethod
    def _is_heading_only(text: str, *, heading: str | None) -> bool:
        if not heading:
            return False
        heading_lines = {heading, *(f"{'#' * level} {heading}" for level in range(1, 7))}
        return text.strip() in heading_lines

    def _split_candidate(self, candidate: ChunkCandidate) -> list[ChunkCandidate]:
        if candidate.chunk_type != "prose":
            return [candidate]

        if len(candidate.text) <= self.config.chunk_size:
            return [candidate]

        pieces: list[ChunkCandidate] = []
        parts = split_semantic_parts(candidate.text)
        heading_prefix: str | None = None

        if parts and is_heading_line(parts[0]):
            heading_prefix = parts.pop(0)

        current = ""

        for part in parts:
            if heading_prefix:
                part = f"{heading_prefix}\n\n{part}"
                heading_prefix = None

            if not current:
                current = part
                continue

            proposed = f"{current}\n\n{part}"

            if len(proposed) <= self.config.chunk_size:
                current = proposed
                continue

            pieces.extend(self._hard_split_text(current, candidate))
            current = part

        if current:
            pieces.extend(self._hard_split_text(current, candidate))

        return pieces

    def _hard_split_text(self, text: str, candidate: ChunkCandidate) -> list[ChunkCandidate]:
        if len(text) <= self.config.chunk_size:
            return [
                ChunkCandidate(
                    text=text.strip(),
                    heading=candidate.heading,
                    section_path=candidate.section_path,
                    chunk_type=candidate.chunk_type,
                    metadata=candidate.metadata,
                    apply_overlap=candidate.apply_overlap,
                )
            ]

        parts: list[ChunkCandidate] = []
        start = 0

        while start < len(text):
            end = min(start + self.config.chunk_size, len(text))
            parts.append(
                ChunkCandidate(
                    text=text[start:end].strip(),
                    heading=candidate.heading,
                    section_path=candidate.section_path,
                    chunk_type=candidate.chunk_type,
                    metadata=candidate.metadata,
                    apply_overlap=candidate.apply_overlap,
                )
            )
            start = end

        return parts

    def _with_overlap(self, previous_text: str | None, current_text: str) -> str:
        if not previous_text or self.config.chunk_overlap == 0:
            return current_text

        overlap = previous_text[-self.config.chunk_overlap :].strip()

        if not overlap:
            return current_text

        return f"{overlap}\n\n{current_text}"


def split_semantic_parts(text: str) -> list[str]:
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    parts: list[str] = []

    for paragraph in paragraphs:
        lines = paragraph.split("\n")

        if len(lines) > 1:
            parts.extend(line.strip() for line in lines if line.strip())
        else:
            parts.append(paragraph)

    return parts


def is_heading_line(text: str) -> bool:
    return text.lstrip().startswith("#")

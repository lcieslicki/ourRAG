from dataclasses import dataclass

from app.domain.parsers.base import ParsedBlock, ParsedDocument

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


@dataclass(frozen=True)
class ChunkCandidate:
    text: str
    heading: str | None
    section_path: tuple[str, ...]


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
    ) -> tuple[DocumentChunk, ...]:
        chunks: list[DocumentChunk] = []

        for candidate in self._build_candidates(parsed_document):
            for piece in self._split_candidate(candidate):
                text = self._with_overlap(chunks[-1].text if chunks else None, piece.text)
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
                    )
                )

        return tuple(chunks)

    def _build_candidates(self, parsed_document: ParsedDocument) -> list[ChunkCandidate]:
        candidates: list[ChunkCandidate] = []
        current_lines: list[str] = []
        current_section_path: tuple[str, ...] = ()
        current_heading: str | None = None

        def flush() -> None:
            if current_lines:
                candidates.append(
                    ChunkCandidate(
                        text="\n\n".join(current_lines).strip(),
                        heading=current_heading,
                        section_path=current_section_path,
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

    def _split_candidate(self, candidate: ChunkCandidate) -> list[ChunkCandidate]:
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

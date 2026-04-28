"""
Table-aware markdown chunking strategy (A7 FR-5).

Preserves:
- header row in every table sub-chunk
- surrounding heading context
- row semantics not split arbitrarily

Uses the existing table detection and parsing infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.chunking.markdown import ChunkCandidate, ChunkingConfig, DocumentChunk, MarkdownChunkingService
from app.domain.chunking.tables import (
    MarkdownTableMatch,
    build_chunk_metadata,
    detect_markdown_tables,
    parse_markdown_table,
    split_text_around_tables,
)
from app.domain.parsers.base import ParsedDocument


@dataclass(frozen=True)
class TableAwareConfig:
    chunk_size: int = 1200
    chunk_overlap: int = 0  # no overlap for table chunks
    max_rows_per_chunk: int = 20
    repeat_header_in_row_chunks: bool = True


class TableAwareMarkdownChunkingService:
    """
    Extends baseline chunking with explicit table-aware handling:
    - table row chunks always include the header row as context
    - can limit rows per chunk via max_rows_per_chunk
    """

    def __init__(self, config: TableAwareConfig | None = None) -> None:
        self.config = config or TableAwareConfig()
        # Reuse baseline for prose (no overlap for table-aware)
        self._baseline = MarkdownChunkingService(
            ChunkingConfig(
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap,
                strategy_version="markdown_table_aware_v1",
            )
        )

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
        # Delegate to baseline; then re-process table candidates with our logic
        # We override _candidates_from_text to get better table handling
        chunks: list[DocumentChunk] = []

        for candidate in self._build_candidates(parsed_document, document_id=document_id, document_name=document_name):
            for piece in self._split_candidate(candidate):
                chunks.append(
                    DocumentChunk(
                        chunk_index=len(chunks),
                        text=piece.text,
                        heading=piece.heading,
                        section_path=piece.section_path,
                        document_version_id=document_version_id,
                        workspace_id=workspace_id,
                        language=language,
                        chunking_strategy_version="markdown_table_aware_v1",
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
            return [ChunkCandidate(text=text, heading=heading, section_path=section_path)]

        candidates: list[ChunkCandidate] = []
        for part_type, value in split_text_around_tables(text, table_matches):
            if part_type == "prose":
                prose = str(value).strip()
                if prose:
                    candidates.append(ChunkCandidate(text=prose, heading=heading, section_path=section_path))
                continue

            if not isinstance(value, MarkdownTableMatch):
                continue

            table = parse_markdown_table(value.lines)
            if table is None:
                continue

            # Table-aware: group rows into batches, each batch includes header row
            header_line = value.lines[0]  # raw header
            separator_line = value.lines[1]  # separator

            row_lines = list(value.lines[2:])
            batch_size = self.config.max_rows_per_chunk

            for batch_start in range(0, max(1, len(row_lines)), batch_size):
                batch = row_lines[batch_start: batch_start + batch_size]
                if not batch:
                    break

                if self.config.repeat_header_in_row_chunks:
                    chunk_lines = [header_line, separator_line] + batch
                else:
                    chunk_lines = (
                        [header_line, separator_line] + batch
                        if batch_start == 0
                        else batch
                    )

                chunk_text = "\n".join(chunk_lines)
                # Prepend heading for context
                if heading:
                    chunk_text = f"{heading}\n\n{chunk_text}"

                candidates.append(
                    ChunkCandidate(
                        text=chunk_text,
                        heading=heading,
                        section_path=section_path,
                        chunk_type="table_row",
                        metadata={
                            "table_aware": True,
                            "row_batch_start": batch_start,
                            "row_count": len(batch),
                            "header_repeated": self.config.repeat_header_in_row_chunks,
                        },
                        apply_overlap=False,
                    )
                )

        return candidates

    def _split_candidate(self, candidate: ChunkCandidate) -> list[ChunkCandidate]:
        # Reuse baseline splitting for prose chunks
        return self._baseline._split_candidate(candidate)

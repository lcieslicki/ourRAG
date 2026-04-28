"""
Citation service: builds normalized citation payloads from retrieved chunks.

Distinguishes between:
- retrieved_sources: all chunks that reached the final prompt context
- cited_sources: top-N subset exposed to the user as explicit support
"""

from dataclasses import dataclass
from typing import Sequence

from app.domain.services.retrieval import RetrievedChunk


@dataclass(frozen=True)
class CitationDTO:
    citation_id: str
    workspace_id: str
    document_id: str
    document_version_id: str
    chunk_id: str
    chunk_index: int
    document_title: str
    heading: str | None
    section_path: tuple[str, ...]
    excerpt: str
    language: str | None
    retrieval_score: float
    rank: int
    # optional
    category: str | None = None
    filename: str | None = None
    storage_uri: str | None = None
    version_label: str | None = None


class CitationService:
    """Builds citation payloads from retrieved chunks."""

    def __init__(
        self,
        *,
        max_exposed_citations: int = 3,
        excerpt_max_chars: int = 300,
        include_retrieved_sources: bool = True,
        include_cited_sources: bool = True,
    ) -> None:
        self.max_exposed_citations = max_exposed_citations
        self.excerpt_max_chars = excerpt_max_chars
        self.include_retrieved_sources = include_retrieved_sources
        self.include_cited_sources = include_cited_sources

    def build_retrieved_sources(
        self,
        workspace_id: str,
        final_chunks: Sequence[RetrievedChunk],
    ) -> list[CitationDTO]:
        """All chunks that reached the final prompt context."""
        return [
            self._to_dto(workspace_id=workspace_id, chunk=chunk, rank=rank)
            for rank, chunk in enumerate(final_chunks, start=1)
        ]

    def select_cited_sources(
        self,
        workspace_id: str,
        final_chunks: Sequence[RetrievedChunk],
    ) -> list[CitationDTO]:
        """
        Deterministic v1 rule:
        - deduplicate by chunk_id (keep first occurrence)
        - take top max_exposed_citations in final ordering
        """
        seen: set[str] = set()
        unique_chunks: list[RetrievedChunk] = []

        for chunk in final_chunks:
            if chunk.chunk_id not in seen:
                seen.add(chunk.chunk_id)
                unique_chunks.append(chunk)

        top_chunks = unique_chunks[: self.max_exposed_citations]
        return [
            self._to_dto(workspace_id=workspace_id, chunk=chunk, rank=rank)
            for rank, chunk in enumerate(top_chunks, start=1)
        ]

    def _to_dto(
        self,
        *,
        workspace_id: str,
        chunk: RetrievedChunk,
        rank: int,
    ) -> CitationDTO:
        heading = chunk.section_path[-1] if chunk.section_path else None
        excerpt = self._truncate(chunk.chunk_text, self.excerpt_max_chars)

        return CitationDTO(
            citation_id=f"cit_{rank:03d}",
            workspace_id=workspace_id,
            document_id=chunk.document_id,
            document_version_id=chunk.document_version_id,
            chunk_id=chunk.chunk_id,
            chunk_index=chunk.payload.get("chunk_index", 0) if isinstance(chunk.payload, dict) else 0,
            document_title=chunk.document_title or "Untitled",
            heading=heading,
            section_path=chunk.section_path,
            excerpt=excerpt,
            language=chunk.language,
            retrieval_score=chunk.score,
            rank=rank,
            category=chunk.category,
        )

    @staticmethod
    def _truncate(text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        # truncate at word boundary if possible
        truncated = text[:max_chars]
        last_space = truncated.rfind(" ")
        if last_space > max_chars // 2:
            return truncated[:last_space] + "…"
        return truncated + "…"

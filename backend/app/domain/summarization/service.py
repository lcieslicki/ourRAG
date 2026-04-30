from app.domain.llm import LlmGateway
from app.domain.summarization.models import (
    SummarizationRequest,
    SummarizationResult,
    SummaryFormat,
)
from app.domain.summarization.orchestrator import SummarizationOrchestrator


class SummarizationService:
    """High-level service for handling summarization requests."""

    def __init__(
        self,
        llm_gateway: LlmGateway,
        max_source_chunks: int = 12,
    ) -> None:
        """
        Initialize the summarization service.

        Args:
            llm_gateway: LLM gateway for text generation.
            max_source_chunks: Maximum number of chunks before using map-reduce.
        """
        self.llm_gateway = llm_gateway
        self.max_source_chunks = max_source_chunks
        self.orchestrator = SummarizationOrchestrator(llm_gateway)

    def summarize(
        self,
        request: SummarizationRequest,
        chunks: list[str],
    ) -> SummarizationResult:
        """
        Process a summarization request.

        Args:
            request: The summarization request containing format and scope.
            chunks: List of text chunks to summarize.

        Returns:
            A SummarizationResult with the generated summary.
        """
        summary_text = self.orchestrator.summarize(
            chunks=chunks,
            format=request.format,
            max_chunks=self.max_source_chunks,
        )

        # Extract source attribution from chunk metadata if available
        sources = self._extract_sources(chunks)

        result = SummarizationResult(
            mode="summarization",
            format=request.format,
            scope=request.scope,
            summary=summary_text,
            sources=sources,
        )

        return result

    def _extract_sources(self, chunks: list[str] | list[dict]) -> list[dict]:
        """
        Extract source attribution from chunks.

        Args:
            chunks: List of text chunks (strings) or chunk dicts with metadata.

        Returns:
            List of source attribution dictionaries.
        """
        # TODO: In a full implementation, this would extract metadata from chunks
        # For now, handle both plain strings and dict-based chunks for forward compatibility
        sources = []
        for chunk in chunks:
            if isinstance(chunk, dict):
                # If chunk has metadata, extract source info
                if "source" in chunk:
                    sources.append(chunk["source"])
                elif "document_id" in chunk:
                    sources.append({
                        "document_id": chunk["document_id"],
                        "type": "document"
                    })
            # For plain strings, we would need document store lookup (out of scope)
        return sources

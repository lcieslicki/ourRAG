from app.domain.llm import GenerationRequest, LlmGateway
from app.domain.prompting import PromptMessage
from app.domain.summarization.models import SummaryFormat
from app.domain.summarization.prompt_builder import SummarizationPromptBuilder


class SummarizationOrchestrator:
    """Orchestrates summarization using direct or map-reduce strategies."""

    def __init__(self, llm_gateway: LlmGateway) -> None:
        """
        Initialize the orchestrator.

        Args:
            llm_gateway: LLM gateway for text generation.
        """
        self.llm_gateway = llm_gateway
        self.prompt_builder = SummarizationPromptBuilder()

    def summarize(
        self,
        chunks: list[str],
        format: SummaryFormat,
        max_chunks: int,
    ) -> str:
        """
        Summarize chunks, auto-selecting between direct and map-reduce methods.

        Args:
            chunks: List of text chunks to summarize.
            format: Desired summary format.
            max_chunks: Threshold for choosing summarization method.

        Returns:
            The generated summary.
        """
        if len(chunks) <= max_chunks:
            return self.summarize_direct(chunks, format)
        else:
            return self.summarize_map_reduce(chunks, format)

    def summarize_direct(
        self,
        chunks: list[str],
        format: SummaryFormat,
    ) -> str:
        """
        Directly summarize chunks in a single LLM call.

        Args:
            chunks: List of text chunks to summarize.
            format: Desired summary format.

        Returns:
            The generated summary.
        """
        prompt = self.prompt_builder.build_summary_prompt(
            format=format,
            chunks=chunks,
        )

        response = self.llm_gateway.generate(
            GenerationRequest(
                messages=(
                    PromptMessage(role="user", content=prompt),
                ),
            )
        )

        return response.text

    def summarize_map_reduce(
        self,
        chunks: list[str],
        format: SummaryFormat,
        batch_size: int = 4,
    ) -> str:
        """
        Summarize chunks using map-reduce strategy for long documents.

        Args:
            chunks: List of text chunks to summarize.
            format: Desired summary format.
            batch_size: Number of chunks to summarize in each partial summary.

        Returns:
            The reduced final summary.
        """
        # Map phase: create batches and generate partial summaries
        partial_summaries = []
        total_parts = (len(chunks) + batch_size - 1) // batch_size

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            part_index = i // batch_size

            prompt = self.prompt_builder.build_partial_summary_prompt(
                chunks=batch,
                part_index=part_index,
                total_parts=total_parts,
            )

            response = self.llm_gateway.generate(
                GenerationRequest(
                    messages=(
                        PromptMessage(role="user", content=prompt),
                    ),
                )
            )

            partial_summaries.append(response.text)

        # Reduce phase: combine partial summaries into final summary
        reduce_prompt = self.prompt_builder.build_reduce_prompt(
            partial_summaries=partial_summaries,
            format=format,
        )

        final_response = self.llm_gateway.generate(
            GenerationRequest(
                messages=(
                    PromptMessage(role="user", content=reduce_prompt),
                ),
            )
        )

        return final_response.text

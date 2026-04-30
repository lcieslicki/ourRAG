from app.domain.summarization.models import SummaryFormat


class SummarizationPromptBuilder:
    """Builds prompts for summarization tasks with format-specific instructions."""

    def build_summary_prompt(
        self,
        format: SummaryFormat,
        chunks: list[str],
        scope_hint: str = "",
    ) -> str:
        """
        Build a summary prompt with format-specific instructions.

        Args:
            format: The desired summary format.
            chunks: List of document chunks to summarize.
            scope_hint: Optional context about the summary scope.

        Returns:
            A formatted prompt string ready for the LLM.
        """
        context = "\n\n".join(chunks)
        scope_context = f"\nScope: {scope_hint}" if scope_hint else ""

        format_instructions = self._get_format_instructions(format)

        prompt = f"""You are a professional summarization assistant. Analyze the following document chunks and create a summary.

{format_instructions}

Document chunks to summarize:
{context}{scope_context}

Generate the summary now:"""

        return prompt

    def build_partial_summary_prompt(
        self,
        chunks: list[str],
        part_index: int,
        total_parts: int,
    ) -> str:
        """
        Build a prompt for partial summarization in map-reduce workflow.

        Args:
            chunks: List of chunks for this partial summary.
            part_index: Zero-based index of this part.
            total_parts: Total number of parts.

        Returns:
            A formatted prompt string for partial summarization.
        """
        context = "\n\n".join(chunks)

        prompt = f"""You are a professional summarization assistant. Analyze the following document chunks (part {part_index + 1} of {total_parts}) and create a concise summary.

Focus on key points and important information. This is part of a larger document that will be further summarized.

Document chunks:
{context}

Generate a concise summary of these chunks:"""

        return prompt

    def build_reduce_prompt(
        self,
        partial_summaries: list[str],
        format: SummaryFormat,
    ) -> str:
        """
        Build a prompt for reducing multiple partial summaries into a final summary.

        Args:
            partial_summaries: List of partial summaries to combine.
            format: The desired final summary format.

        Returns:
            A formatted prompt string for reduction.
        """
        summaries_text = "\n\n".join(
            [f"Partial Summary {i + 1}:\n{s}" for i, s in enumerate(partial_summaries)]
        )

        format_instructions = self._get_format_instructions(format)

        prompt = f"""You are a professional summarization assistant. You have received multiple partial summaries of a document. Your task is to synthesize them into a cohesive final summary.

{format_instructions}

Partial summaries to combine:
{summaries_text}

Generate the final summary now:"""

        return prompt

    def _get_format_instructions(self, format: SummaryFormat) -> str:
        """Get format-specific instructions for the LLM."""
        if format == SummaryFormat.plain_summary:
            return """Format: Plain prose summary
Provide a flowing, narrative summary in complete sentences. Aim for clarity and readability."""

        elif format == SummaryFormat.bullet_brief:
            return """Format: Bullet point brief
Provide a structured list of bullet points capturing key information. Each point should be concise and clear."""

        elif format == SummaryFormat.checklist:
            return """Format: Actionable checklist
Provide a checklist of actionable items, decisions, or steps. Format each item as an actionable task or decision point."""

        elif format == SummaryFormat.key_points_and_risks:
            return """Format: Key Points and Risks
Provide two clearly separated sections:
1. Key Points: Main takeaways and important information
2. Risks: Potential risks, concerns, or important caveats"""

        else:
            return "Provide a clear and concise summary."

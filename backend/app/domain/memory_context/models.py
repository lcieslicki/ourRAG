from pydantic import BaseModel, Field


class ContextualizedTurn(BaseModel):
    """Represents a contextualized user message.

    Attributes:
        original_query: The original user message before contextualization.
        contextualized_query: The rewritten query as a standalone question.
        was_contextualized: Whether the message was actually contextualized.
        used_summary: Whether the summary was used during contextualization.
        used_recent_turns: Number of recent conversation turns used.
        metadata: Additional metadata about the contextualization process.
    """
    original_query: str
    contextualized_query: str
    was_contextualized: bool
    used_summary: bool
    used_recent_turns: int
    metadata: dict = Field(default_factory=dict)


class RetrievalMemoryPackage(BaseModel):
    """Memory package optimized for retrieval (search intent).

    Attributes:
        recent_messages: Last N messages for retrieval context.
        summary_snippet: Truncated summary of older conversation (if available).
        message_count: Total number of messages included.
    """
    recent_messages: list[dict] = Field(default_factory=list)
    summary_snippet: str | None = None
    message_count: int = 0


class GenerationMemoryPackage(BaseModel):
    """Memory package optimized for generation (answer shaping).

    Attributes:
        recent_messages: Last N messages for generation context.
        summary_snippet: Truncated summary of older conversation (if available).
        message_count: Total number of messages included.
    """
    recent_messages: list[dict] = Field(default_factory=list)
    summary_snippet: str | None = None
    message_count: int = 0


class AdvancedMemoryPackage(BaseModel):
    """Complete advanced memory package with both retrieval and generation contexts.

    Attributes:
        retrieval: Memory package optimized for search/retrieval.
        generation: Memory package optimized for answer generation.
        contextualized_turn: Information about user message contextualization (optional).
    """
    retrieval: RetrievalMemoryPackage
    generation: GenerationMemoryPackage
    contextualized_turn: ContextualizedTurn | None = None

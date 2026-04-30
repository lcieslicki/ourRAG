from pydantic import BaseModel, Field, PositiveInt


class AdvancedMemoryConfig(BaseModel):
    """Configuration for advanced memory contextualization and retrieval/generation separation.

    Attributes:
        memory_contextualization_enabled: Whether to enable message contextualization.
        memory_retrieval_recent_message_limit: Max recent messages for retrieval context.
        memory_generation_recent_message_limit: Max recent messages for generation context.
        memory_summary_max_chars: Maximum characters to include in summary snippets.
        memory_contextualization_timeout_ms: Timeout for contextualization LLM calls.
    """
    memory_contextualization_enabled: bool = Field(default=True)
    memory_retrieval_recent_message_limit: PositiveInt = Field(default=4)
    memory_generation_recent_message_limit: PositiveInt = Field(default=6)
    memory_summary_max_chars: PositiveInt = Field(default=2000)
    memory_contextualization_timeout_ms: PositiveInt = Field(default=2500)

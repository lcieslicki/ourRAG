from pydantic import BaseModel, Field, PositiveInt, field_validator


class QueryRewriteConfig(BaseModel):
    """Configuration for query rewriting and multi-query retrieval.

    Attributes:
        query_rewrite_mode: Rewrite mode - 'disabled', 'single_rewrite', or 'multi_query'.
        query_rewrite_max_queries: Maximum number of rewritten queries to generate.
        query_rewrite_include_summary: Include conversation summary in rewrite context.
        query_rewrite_include_recent_messages: Include recent messages in rewrite context.
        query_rewrite_model_provider: LLM provider for query rewriting ('ollama').
        query_rewrite_timeout_ms: Timeout in milliseconds for rewrite operations.
    """
    query_rewrite_mode: str = Field(default="disabled")
    query_rewrite_max_queries: PositiveInt = Field(default=3)
    query_rewrite_include_summary: bool = Field(default=True)
    query_rewrite_include_recent_messages: bool = Field(default=True)
    query_rewrite_model_provider: str = Field(default="ollama")
    query_rewrite_timeout_ms: PositiveInt = Field(default=3000)

    @field_validator("query_rewrite_mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        """Validate that mode is one of the allowed values."""
        allowed = {"disabled", "single_rewrite", "multi_query"}
        if value not in allowed:
            raise ValueError(f"query_rewrite_mode must be one of {allowed}, got '{value}'")
        return value

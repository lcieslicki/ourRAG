from pydantic import BaseModel, Field
from app.domain.summarization.models import SummaryFormat, SummaryScope


class SummarizeRequestSchema(BaseModel):
    """Request schema for the summarize endpoint."""

    workspace_id: str
    format: SummaryFormat
    scope: SummaryScope
    query: str | None = Field(default=None, description="Optional query context")


class SummarizeResponseSchema(BaseModel):
    """Response schema for the summarize endpoint."""

    mode: str = "summarization"
    format: SummaryFormat
    scope: SummaryScope
    summary: str
    sources: list[dict] = Field(default_factory=list)
    debug_metadata: dict | None = None

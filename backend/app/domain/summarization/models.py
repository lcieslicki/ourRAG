from enum import Enum
from pydantic import BaseModel, Field


class SummaryFormat(str, Enum):
    """Enumeration of supported summary formats."""
    plain_summary = "plain_summary"
    bullet_brief = "bullet_brief"
    checklist = "checklist"
    key_points_and_risks = "key_points_and_risks"


class SummaryScope(BaseModel):
    """Scope definition for summarization."""
    document_id: str | None = None
    section_path: list[str] = Field(default_factory=list)
    use_retrieved_context: bool = False


class SummarizationRequest(BaseModel):
    """Request model for summarization endpoint."""
    workspace_id: str
    format: SummaryFormat
    scope: SummaryScope
    query: str | None = None


class SummarizationResult(BaseModel):
    """Result model for summarization response."""
    mode: str = "summarization"
    format: SummaryFormat
    scope: SummaryScope
    summary: str
    sources: list[dict] = Field(default_factory=list)
    debug_metadata: dict | None = None

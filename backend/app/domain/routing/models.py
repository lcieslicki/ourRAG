from enum import Enum

from pydantic import BaseModel, Field


class ResponseMode(str, Enum):
    """Supported response modes for routing decisions."""
    qa = "qa"
    summarization = "summarization"
    structured_extraction = "structured_extraction"
    admin_lookup = "admin_lookup"
    refuse_out_of_scope = "refuse_out_of_scope"


class RouteDecision(BaseModel):
    """Decision output from the router."""
    selected_mode: ResponseMode = Field(..., description="The selected response mode")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in the routing decision")
    router_strategy: str = Field(..., description="The strategy used for routing (e.g., 'disabled_default', 'classification', 'ui_hint')")
    router_reason: str = Field(..., description="Explanation of why this mode was selected")
    is_fallback: bool = Field(default=False, description="Whether this is a fallback decision due to low confidence")


class RequestContext(BaseModel):
    """Context for a routing request."""
    query: str = Field(..., description="The user query")
    workspace_id: str = Field(..., description="The workspace ID")
    conversation_id: str | None = Field(default=None, description="The conversation ID if available")
    ui_mode_hint: str | None = Field(default=None, description="Optional UI hint for preferred mode")
    recent_turns: list[dict] = Field(default_factory=list, description="Recent conversation turns")
    summary: str | None = Field(default=None, description="Conversation summary if available")
    query_classification: dict | None = Field(default=None, description="Query classification result if available")


class ResponseEnvelope(BaseModel):
    """Envelope for all capability responses."""
    selected_mode: ResponseMode = Field(..., description="The mode that was executed")
    router_reason: str = Field(..., description="Explanation of routing decision")
    router_strategy: str = Field(..., description="The strategy used for routing")
    content: dict = Field(..., description="The capability-specific content")
    sources: list[dict] = Field(default_factory=list, description="Source attribution")
    debug_metadata: dict | None = Field(default=None, description="Optional debug metadata")

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class CitationResponse(BaseModel):
    citation_id: str
    workspace_id: str
    document_id: str
    document_version_id: str
    chunk_id: str
    chunk_index: int
    document_title: str
    heading: str | None
    section_path: list[str]
    excerpt: str
    language: str | None
    retrieval_score: float
    rank: int
    # optional
    category: str | None = None
    filename: str | None = None
    storage_uri: str | None = None
    version_label: str | None = None


class ConversationSummaryResponse(BaseModel):
    id: str
    workspace_id: str
    user_id: str
    title: str | None
    status: str
    selected_scope: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class CreateConversationRequest(BaseModel):
    workspace_id: str
    title: str | None = Field(default=None, max_length=255)
    selected_scope: dict[str, Any] | None = None


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    workspace_id: str
    user_id: str | None
    role: Literal["user", "assistant", "system"]
    content: str
    response_metadata: dict[str, Any] | None = None
    created_at: datetime


class ConversationDetailResponse(ConversationSummaryResponse):
    messages: list[MessageResponse]
    summary: str | None = None


class ChatRequest(BaseModel):
    workspace_id: str
    conversation_id: str
    message: str = Field(min_length=1)
    scope: dict[str, Any] | None = None


class ChatAssistantMessageResponse(BaseModel):
    id: str
    role: Literal["assistant"]
    content: str
    # legacy compatibility field — maps to cited_sources
    sources: list[dict[str, Any]] = Field(default_factory=list)
    # normalized citation payload (Step 2)
    retrieved_sources: list[CitationResponse] = Field(default_factory=list)
    cited_sources: list[CitationResponse] = Field(default_factory=list)
    response_mode: str = "answer_from_context"
    guardrail_reason: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    user_message: MessageResponse
    assistant_message: ChatAssistantMessageResponse
    usage: dict[str, Any] = Field(default_factory=dict)

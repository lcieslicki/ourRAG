from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


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
    sources: list[dict[str, Any]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    conversation_id: str
    user_message: MessageResponse
    assistant_message: ChatAssistantMessageResponse
    usage: dict[str, Any] = Field(default_factory=dict)

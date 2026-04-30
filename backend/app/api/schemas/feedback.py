from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class FeedbackSubmitSchema(BaseModel):
    """Schema for submitting feedback."""
    conversation_id: str
    message_id: str | None = None
    helpfulness: Literal["helpful", "not_helpful"] | None = None
    source_quality: Literal["source_useful", "source_not_useful"] | None = None
    answer_completeness: Literal["answer_complete", "answer_incomplete"] | None = None
    comment: str | None = Field(default=None, max_length=1000)
    response_mode: str | None = None
    cited_source_ids: list[str] | None = None

    @field_validator("comment")
    @classmethod
    def validate_comment_length(cls, v: str | None) -> str | None:
        if v and len(v) > 1000:
            raise ValueError("Comment must be at most 1000 characters")
        return v


class FeedbackResponseSchema(BaseModel):
    """Schema for a single feedback response."""
    id: str
    workspace_id: str
    conversation_id: str
    message_id: str | None
    helpfulness: str | None
    source_quality: str | None
    answer_completeness: str | None
    comment: str | None
    response_mode: str | None
    cited_source_ids: list[str] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FeedbackListResponseSchema(BaseModel):
    """Schema for listing feedback with pagination."""
    items: list[FeedbackResponseSchema]
    total: int
    limit: int
    offset: int


class FeedbackSummarySchema(BaseModel):
    """Schema for feedback summary statistics."""
    total: int
    helpful_count: int
    not_helpful_count: int
    source_useful_count: int
    source_not_useful_count: int

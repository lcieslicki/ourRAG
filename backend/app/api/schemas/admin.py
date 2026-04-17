from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProcessingJobResponse(BaseModel):
    id: str
    document_version_id: str
    document_id: str
    document_title: str
    job_type: str
    status: str
    attempts: int
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WorkspaceSettingsResponse(BaseModel):
    workspace_id: str
    name: str
    slug: str
    status: str
    default_language: str
    system_prompt_override: str | None
    llm_model_override: str | None
    embedding_model_override: str | None
    settings: dict[str, Any]


class WorkspaceSettingsUpdateRequest(BaseModel):
    default_language: str | None = Field(default=None, max_length=16)
    system_prompt_override: str | None = None
    llm_model_override: str | None = Field(default=None, max_length=255)
    embedding_model_override: str | None = Field(default=None, max_length=255)
    settings: dict[str, Any] | None = None

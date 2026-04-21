from datetime import datetime
from typing import Any, Literal

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


class UserCreateRequest(BaseModel):
    email: str = Field(max_length=320)
    display_name: str = Field(max_length=255)


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    status: str
    created_at: datetime


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(max_length=255)
    slug: str = Field(max_length=120)


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    slug: str
    status: str
    data_folder: str | None
    created_at: datetime


class WorkspaceMemberAddRequest(BaseModel):
    user_id: str
    role: Literal["owner", "admin", "member", "viewer"] = "owner"


class WorkspaceMemberResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    role: str


class AdminDocumentIndexResult(BaseModel):
    document_id: str
    document_version_id: str
    title: str
    file_name: str


class AdminIndexFailure(BaseModel):
    file_name: str
    error: str


class AdminDocumentUploadResponse(BaseModel):
    indexed: list[AdminDocumentIndexResult]
    failed: list[AdminIndexFailure]


class AdminFolderIndexRequest(BaseModel):
    user_id: str
    folder: str | None = Field(default=None, max_length=255)


class AdminSetDataFolderRequest(BaseModel):
    folder: str = Field(max_length=255)


class AdminFolderIndexResponse(BaseModel):
    folder: str
    files_found: int
    indexed: list[AdminDocumentIndexResult]
    failed: list[AdminIndexFailure]


class AdminDocumentListItemResponse(BaseModel):
    id: str
    title: str
    category: str
    tags: list[str]
    status: str
    language: str | None
    latest_processing_status: str | None
    latest_version_id: str | None
    latest_version_number: int | None
    chunk_count: int | None
    indexed_at: datetime | None
    embedding_model_name: str | None
    embedding_model_version: str | None
    is_active: bool | None
    is_invalidated: bool | None
    qdrant_vector_count: int | None
    latest_error_message: str | None
    latest_error_job_type: str | None
    version_count: int


class AdminDocumentDeleteResponse(BaseModel):
    document_id: str
    deleted_versions: int


class AdminDocumentsBulkDeleteResponse(BaseModel):
    deleted_documents: int
    deleted_versions: int


class AdminDocumentsBulkReindexResponse(BaseModel):
    queued_jobs: int
    skipped_documents: int

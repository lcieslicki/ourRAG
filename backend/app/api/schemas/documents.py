from datetime import datetime

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    document_id: str
    document_version_id: str
    workspace_id: str
    title: str
    category: str
    version_number: int
    file_name: str
    mime_type: str
    processing_status: str
    is_active: bool


class DocumentVersionLifecycleResponse(BaseModel):
    document_id: str
    document_version_id: str
    workspace_id: str
    version_number: int
    processing_status: str
    is_active: bool
    is_invalidated: bool
    invalidated_reason: str | None = None


class InvalidateDocumentVersionRequest(BaseModel):
    reason: str | None = None


class DocumentVersionReindexResponse(BaseModel):
    document_id: str
    document_version_id: str
    workspace_id: str
    job_id: str
    job_type: str
    job_status: str


class DocumentVersionResponse(BaseModel):
    id: str
    document_id: str
    version_number: int
    file_name: str
    mime_type: str
    language: str
    is_active: bool
    is_invalidated: bool
    invalidated_reason: str | None
    processing_status: str
    chunk_count: int
    embedding_model_name: str | None
    embedding_model_version: str | None
    chunking_strategy_version: str | None
    indexed_at: datetime | None
    created_by_user_id: str


class DocumentListItemResponse(BaseModel):
    id: str
    workspace_id: str
    title: str
    slug: str
    category: str
    tags: list[str]
    status: str
    active_version_id: str | None
    latest_processing_status: str | None
    version_count: int


class DocumentDetailResponse(BaseModel):
    id: str
    workspace_id: str
    title: str
    slug: str
    category: str
    tags: list[str]
    status: str
    versions: list[DocumentVersionResponse]

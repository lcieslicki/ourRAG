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

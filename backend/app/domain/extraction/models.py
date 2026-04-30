from enum import Enum

from pydantic import BaseModel, Field


class ExtractionMode(str, Enum):
    """Enumeration of extraction modes."""
    extract_from_selected_documents = "extract_from_selected_documents"
    extract_from_retrieved_context = "extract_from_retrieved_context"


class ExtractionStatus(str, Enum):
    """Enumeration of extraction result statuses."""
    success = "success"
    validation_failure = "validation_failure"
    timeout = "timeout"
    no_context = "no_context"


class ExtractionRequest(BaseModel):
    """Request model for structured extraction."""
    workspace_id: str = Field(..., description="Workspace identifier")
    schema_name: str = Field(..., description="Name of the extraction schema")
    mode: ExtractionMode = Field(..., description="Extraction mode")
    document_ids: list[str] = Field(default_factory=list, description="List of document IDs for document mode")
    query: str | None = Field(default=None, description="Query for retrieved context mode")


class ExtractionResult(BaseModel):
    """Response model for structured extraction results."""
    mode: str = Field(default="structured_extraction", description="Extraction operation mode")
    schema_name: str = Field(..., description="Name of the schema used for extraction")
    status: ExtractionStatus = Field(..., description="Status of the extraction operation")
    data: dict | None = Field(default=None, description="Extracted data matching the schema")
    validation_errors: list[str] = Field(default_factory=list, description="Validation error messages")
    sources: list[dict] = Field(default_factory=list, description="Source attribution for extracted data")
    debug_metadata: dict | None = Field(default=None, description="Debug metadata")

from pydantic import BaseModel, Field

from app.domain.extraction.models import ExtractionMode, ExtractionStatus


class ExtractionRequestSchema(BaseModel):
    """FastAPI schema for extraction request."""

    workspace_id: str = Field(..., description="Workspace identifier")
    schema_name: str = Field(..., description="Name of the extraction schema")
    mode: ExtractionMode = Field(..., description="Extraction mode")
    document_ids: list[str] = Field(default_factory=list, description="List of document IDs")
    query: str | None = Field(default=None, description="Query for context retrieval")


class ExtractionResponseSchema(BaseModel):
    """FastAPI schema for extraction response."""

    mode: str = Field(default="structured_extraction", description="Operation mode")
    schema_name: str = Field(..., description="Schema name used")
    status: ExtractionStatus = Field(..., description="Extraction status")
    data: dict | None = Field(default=None, description="Extracted data")
    validation_errors: list[str] = Field(default_factory=list, description="Validation errors")
    sources: list[dict] = Field(default_factory=list, description="Source attribution")
    debug_metadata: dict | None = Field(default=None, description="Debug metadata")

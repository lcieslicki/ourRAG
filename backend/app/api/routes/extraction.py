from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user, get_db
from app.api.dependencies.llm import get_generation_gateway
from app.api.schemas.extraction import ExtractionRequestSchema, ExtractionResponseSchema
from app.core.config import get_settings
from app.domain.extraction.models import ExtractionRequest
from app.domain.extraction.service import ExtractionService
from app.domain.llm import LlmGateway

router = APIRouter(prefix="/api/workspaces/{workspace_id}/extract", tags=["extraction"])


@router.post("", response_model=ExtractionResponseSchema)
async def extract_structured_data(
    workspace_id: str,
    payload: ExtractionRequestSchema,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    llm_gateway: Annotated[LlmGateway, Depends(get_generation_gateway)],
) -> ExtractionResponseSchema:
    """
    Extract structured data from documents.

    Args:
        workspace_id: The workspace identifier.
        payload: The extraction request.
        current_user: The current authenticated user.
        db: The database session.
        llm_gateway: The LLM gateway.

    Returns:
        The extraction result.
    """
    settings = get_settings()
    extraction_config = settings.__dict__.get("extraction", {})

    service = ExtractionService(
        llm_gateway=llm_gateway,
        extraction_timeout_ms=extraction_config.get("extraction_timeout_ms", 5000),
        validation_strict=extraction_config.get("extraction_validation_strict", True),
    )

    request = ExtractionRequest(
        workspace_id=workspace_id,
        schema_name=payload.schema_name,
        mode=payload.mode,
        document_ids=payload.document_ids,
        query=payload.query,
    )

    # Note: In a full implementation, chunks would be retrieved from document store
    # For now, pass None to use the default placeholder behavior
    result = await service.extract(request, context_chunks=None)

    return ExtractionResponseSchema(
        mode=result.mode,
        schema_name=result.schema_name,
        status=result.status,
        data=result.data,
        validation_errors=result.validation_errors,
        sources=result.sources,
        debug_metadata=result.debug_metadata,
    )

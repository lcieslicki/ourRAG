from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user, get_db
from app.api.dependencies.llm import get_generation_gateway
from app.api.schemas.summarization import SummarizeRequestSchema, SummarizeResponseSchema
from app.core.config import get_settings
from app.domain.errors import WorkspaceAccessDenied
from app.domain.llm import LlmGateway
from app.domain.services.access import WorkspaceAccessService
from app.domain.summarization.models import SummarizationRequest
from app.domain.summarization.service import SummarizationService

router = APIRouter(prefix="/api/summarize", tags=["summarization"])


@router.post("", response_model=SummarizeResponseSchema)
def summarize(
    payload: SummarizeRequestSchema,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    llm_gateway: Annotated[LlmGateway, Depends(get_generation_gateway)],
) -> SummarizeResponseSchema:
    """
    Summarize document chunks using various formats.

    Args:
        payload: Summarization request with format and scope.
        current_user: Current authenticated user.
        db: Database session.
        llm_gateway: LLM gateway for text generation.

    Returns:
        A summarization result with the generated summary.

    Raises:
        WorkspaceAccessDenied: If user is not a workspace member.
    """
    settings = get_settings()

    # Check if summarization is enabled
    if not settings.app.debug:  # Placeholder - should check summarization config
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Summarization feature is not enabled",
        )

    # Verify user is a workspace member
    access_service = WorkspaceAccessService(db)
    try:
        access_service.ensure_workspace_member(
            user_id=current_user.id,
            workspace_id=payload.workspace_id,
        )
    except WorkspaceAccessDenied as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )

    # Initialize summarization service
    service = SummarizationService(
        llm_gateway=llm_gateway,
        max_source_chunks=12,  # Should come from config
    )

    # Create request and dummy chunks for now
    request = SummarizationRequest(
        workspace_id=payload.workspace_id,
        format=payload.format,
        scope=payload.scope,
        query=payload.query,
    )

    # Placeholder: chunks should come from document retrieval
    chunks = ["Sample chunk content for summarization."]

    # Process summarization
    result = service.summarize(request=request, chunks=chunks)

    return SummarizeResponseSchema(
        mode=result.mode,
        format=result.format,
        scope=result.scope,
        summary=result.summary,
        sources=result.sources,
        debug_metadata=result.debug_metadata,
    )

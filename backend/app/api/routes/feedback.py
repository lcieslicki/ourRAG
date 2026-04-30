from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user, get_db
from app.api.schemas.feedback import (
    FeedbackListResponseSchema,
    FeedbackResponseSchema,
    FeedbackSubmitSchema,
    FeedbackSummarySchema,
)
from app.domain.services.feedback import FeedbackService

router = APIRouter(prefix="/api/workspaces", tags=["feedback"])


@router.post(
    "/{workspace_id}/feedback",
    response_model=FeedbackResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
def submit_feedback(
    workspace_id: str,
    payload: FeedbackSubmitSchema,
    current_user: Annotated[CurrentUser, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
) -> FeedbackResponseSchema:
    """Submit feedback for a message in a conversation."""
    try:
        feedback_record = FeedbackService.submit_feedback(
            db=db,
            workspace_id=workspace_id,
            conversation_id=payload.conversation_id,
            message_id=payload.message_id,
            helpfulness=payload.helpfulness,
            source_quality=payload.source_quality,
            answer_completeness=payload.answer_completeness,
            comment=payload.comment,
            response_mode=payload.response_mode,
            cited_source_ids=payload.cited_source_ids,
        )
        db.commit()
        return FeedbackResponseSchema.model_validate(feedback_record)
    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "validation_error", "message": str(e)},
        )


@router.get("/{workspace_id}/feedback", response_model=FeedbackListResponseSchema)
def list_feedback(
    workspace_id: str,
    limit: int = 100,
    offset: int = 0,
    current_user: Annotated[CurrentUser, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
) -> FeedbackListResponseSchema:
    """List feedback for a workspace."""
    items = FeedbackService.list_feedback(
        db=db,
        workspace_id=workspace_id,
        limit=limit,
        offset=offset,
    )
    return FeedbackListResponseSchema(
        items=[FeedbackResponseSchema.model_validate(item) for item in items],
        total=len(items),
        limit=limit,
        offset=offset,
    )


@router.get("/{workspace_id}/feedback/summary", response_model=FeedbackSummarySchema)
def get_feedback_summary(
    workspace_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
) -> FeedbackSummarySchema:
    """Get feedback summary statistics for a workspace."""
    summary = FeedbackService.get_feedback_summary(db=db, workspace_id=workspace_id)
    return FeedbackSummarySchema(**summary)

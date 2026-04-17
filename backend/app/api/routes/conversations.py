from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user, get_db
from app.api.schemas.conversations import (
    ConversationDetailResponse,
    ConversationSummaryResponse,
    CreateConversationRequest,
    MessageResponse,
)
from app.domain.errors import ConversationAccessDenied, WorkspaceAccessDenied
from app.domain.models import Conversation, Message
from app.domain.services.conversations import ConversationService

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationSummaryResponse])
def list_conversations(
    workspace_id: Annotated[str, Query()],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ConversationSummaryResponse]:
    service = ConversationService(db)
    try:
        conversations = service.list_workspace_conversations(
            user_id=current_user.id,
            workspace_id=workspace_id,
        )
    except WorkspaceAccessDenied as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "workspace_access_denied", "message": str(exc)},
        ) from exc

    return [conversation_summary_response(conversation) for conversation in conversations]


@router.post("", response_model=ConversationSummaryResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: CreateConversationRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ConversationSummaryResponse:
    service = ConversationService(db)
    try:
        conversation = service.create_conversation(
            user_id=current_user.id,
            workspace_id=payload.workspace_id,
            title=payload.title,
            selected_scope=payload.selected_scope,
        )
        db.commit()
    except WorkspaceAccessDenied as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "workspace_access_denied", "message": str(exc)},
        ) from exc

    return conversation_summary_response(conversation)


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(
    conversation_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ConversationDetailResponse:
    service = ConversationService(db)
    try:
        conversation = service.get_conversation(user_id=current_user.id, conversation_id=conversation_id)
    except (ConversationAccessDenied, WorkspaceAccessDenied) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "conversation_not_found", "message": str(exc)},
        ) from exc

    return conversation_detail_response(conversation)


def conversation_summary_response(conversation: Conversation) -> ConversationSummaryResponse:
    return ConversationSummaryResponse(
        id=conversation.id,
        workspace_id=conversation.workspace_id,
        user_id=conversation.user_id,
        title=conversation.title,
        status=conversation.status,
        selected_scope=conversation.selected_scope_json,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


def conversation_detail_response(conversation: Conversation) -> ConversationDetailResponse:
    messages = sorted(conversation.messages, key=lambda message: message.created_at)
    return ConversationDetailResponse(
        **conversation_summary_response(conversation).model_dump(),
        messages=[message_response(message) for message in messages],
        summary=conversation.summary.summary_text if conversation.summary else None,
    )


def message_response(message: Message) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        workspace_id=message.workspace_id,
        user_id=message.user_id,
        role=message.role,
        content=message.content_text,
        response_metadata=message.response_metadata_json,
        created_at=message.created_at,
    )

from typing import Annotated

from fastapi import APIRouter, Depends, Query, WebSocket
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.domain.errors import ConversationAccessDenied, WorkspaceAccessDenied
from app.domain.services.conversations import ConversationService
from app.infrastructure.realtime import chat_log_manager

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.websocket("/ws/{conversation_id}")
async def subscribe_chat_logs(
    websocket: WebSocket,
    conversation_id: str,
    user_id: Annotated[str, Query(alias="user_id")],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    service = ConversationService(db)
    try:
        service.get_conversation(user_id=user_id, conversation_id=conversation_id)
    except (ConversationAccessDenied, WorkspaceAccessDenied):
        await websocket.close(code=4403, reason="conversation_access_denied")
        return

    await chat_log_manager.connect(conversation_id=conversation_id, websocket=websocket)
    await chat_log_manager.keepalive(conversation_id=conversation_id, websocket=websocket)

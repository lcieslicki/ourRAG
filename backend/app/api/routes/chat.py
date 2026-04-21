from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user, get_db
from app.api.dependencies.llm import get_generation_gateway
from app.api.dependencies.retrieval import get_query_embedding_service, get_retrieval_vector_index
from app.api.routes.conversations import message_response
from app.api.schemas.conversations import ChatAssistantMessageResponse, ChatRequest, ChatResponse
from app.core.config import get_settings
from app.domain.embeddings import EmbeddingService
from app.domain.errors import ConversationAccessDenied, DocumentAccessDenied, WorkspaceAccessDenied
from app.domain.llm import GenerationRequest, LlmGateway
from app.domain.prompting import PromptBuilder, PromptBuildInput
from app.domain.services.conversations import ConversationService
from app.domain.services.memory import ConversationMemoryService
from app.domain.services.retrieval import RetrievalScope, RetrievalService, RetrievedChunk, VectorIndexService
from app.infrastructure.llm import OllamaGatewayError
from app.infrastructure.realtime import ChatProcessingEvent, chat_log_manager

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def send_chat_message(
    payload: ChatRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    llm_gateway: Annotated[LlmGateway, Depends(get_generation_gateway)],
    embedding_service: Annotated[EmbeddingService, Depends(get_query_embedding_service)],
    vector_index: Annotated[VectorIndexService, Depends(get_retrieval_vector_index)],
) -> ChatResponse:
    conversation_service = ConversationService(db)
    settings = get_settings()
    active_user_message_id: str | None = None
    active_workspace_id = payload.workspace_id

    async def emit(category: str, stage: str, status: str, event_payload: dict[str, Any]) -> None:
        await chat_log_manager.publish(
            ChatProcessingEvent(
                conversation_id=payload.conversation_id,
                workspace_id=active_workspace_id,
                message_id=active_user_message_id,
                category=category,
                stage=stage,
                status=status,
                payload=event_payload,
                timestamp=datetime.now(UTC).isoformat(),
            )
        )

    def debug_hook(event_name: str, event_payload: dict[str, Any]) -> None:
        category, stage = event_name.split(".", 1) if "." in event_name else ("request", event_name)
        if stage.endswith("completed"):
            event_status = "completed"
        elif stage.endswith("failed"):
            event_status = "failed"
        else:
            event_status = "started"
        event = ChatProcessingEvent(
            conversation_id=payload.conversation_id,
            workspace_id=active_workspace_id,
            message_id=active_user_message_id,
            category=category,
            stage=stage,
            status=event_status,
            payload=event_payload,
            timestamp=datetime.now(UTC).isoformat(),
        )
        import asyncio

        asyncio.create_task(chat_log_manager.publish(event))

    try:
        await emit("request", "started", "started", {"message": payload.message, "scope": payload.scope})
        conversation = conversation_service.get_conversation(
            user_id=current_user.id,
            conversation_id=payload.conversation_id,
        )
        active_workspace_id = conversation.workspace_id
        if conversation.workspace_id != payload.workspace_id:
            raise ConversationAccessDenied("Conversation does not belong to the requested workspace.")
        await emit(
            "request",
            "conversation_validated",
            "completed",
            {"conversation_id": conversation.id, "workspace_id": conversation.workspace_id},
        )

        retrieval_scope = parse_retrieval_scope(payload.scope if payload.scope is not None else conversation.selected_scope_json)
        await emit(
            "request",
            "scope_resolved",
            "completed",
            {
                "category": retrieval_scope.category,
                "document_ids": list(retrieval_scope.document_ids),
                "language": retrieval_scope.language,
            },
        )
        await emit("retrieval", "started", "started", {"query": payload.message})
        retrieval = RetrievalService(
            session=db,
            embedding_service=embedding_service,
            vector_index=vector_index,
            settings=settings,
            debug_hook=debug_hook,
        ).retrieve(
            user_id=current_user.id,
            workspace_id=payload.workspace_id,
            query=payload.message,
            scope=retrieval_scope,
        )
        user_message = conversation_service.append_user_message(
            user_id=current_user.id,
            workspace_id=payload.workspace_id,
            conversation_id=payload.conversation_id,
            content=payload.message,
        )
        active_user_message_id = user_message.id
        await emit(
            "persistence",
            "user_message_saved",
            "completed",
            {"message_id": user_message.id, "content": user_message.content_text},
        )
        await emit("memory", "started", "started", {})
        memory = ConversationMemoryService(session=db, settings=settings).build_memory_package(
            user_id=current_user.id,
            workspace_id=payload.workspace_id,
            conversation_id=payload.conversation_id,
            exclude_message_ids={user_message.id},
        )
        await emit(
            "memory",
            "completed",
            "completed",
            {
                "recent_messages": [
                    {"role": item.role, "content": item.content} for item in memory.prompt_memory.recent_messages
                ],
                "summary": memory.prompt_memory.summary,
            },
        )
        await emit("prompt", "started", "started", {})
        prompt = PromptBuilder().build(
            PromptBuildInput(
                workspace_name=conversation.workspace.name if conversation.workspace else None,
                current_user_message=payload.message,
                memory=memory.prompt_memory,
                retrieved_chunks=retrieval.chunks,
            )
        )
        await emit(
            "prompt",
            "completed",
            "completed",
            {
                "template_version": prompt.template_version,
                "has_retrieval_context": prompt.has_retrieval_context,
                "messages": [{"role": message.role, "content": message.content} for message in prompt.messages],
            },
        )
        generation = llm_gateway.generate(
            GenerationRequest(messages=prompt.messages, metadata={"debug_hook": debug_hook})
        )
        sources = sources_from_chunks(retrieval.chunks)
        assistant_message = conversation_service.append_assistant_message(
            user_id=current_user.id,
            workspace_id=payload.workspace_id,
            conversation_id=payload.conversation_id,
            content=generation.text,
            response_metadata={
                "llm_provider": generation.provider,
                "llm_model": generation.model,
                "finish_reason": generation.finish_reason,
                "prompt_template_version": prompt.template_version,
                "has_retrieval_context": prompt.has_retrieval_context,
                "sources": sources,
            },
        )
        await emit(
            "persistence",
            "assistant_message_saved",
            "completed",
            {
                "message_id": assistant_message.id,
                "content": assistant_message.content_text,
                "sources": sources,
            },
        )
        db.commit()
        await emit("request", "completed", "completed", {"assistant_message_id": assistant_message.id})
    except ValueError as exc:
        db.rollback()
        await emit("error", "request_failed", "failed", {"code": "invalid_message", "message": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_message", "message": str(exc)},
        ) from exc
    except DocumentAccessDenied as exc:
        db.rollback()
        await emit("error", "request_failed", "failed", {"code": "invalid_scope_filter", "message": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_scope_filter", "message": str(exc)},
        ) from exc
    except (ConversationAccessDenied, WorkspaceAccessDenied) as exc:
        db.rollback()
        await emit("error", "request_failed", "failed", {"code": "conversation_not_found", "message": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "conversation_not_found", "message": str(exc)},
        ) from exc
    except OllamaGatewayError as exc:
        db.rollback()
        await emit("error", "request_failed", "failed", {"code": "llm_timeout", "message": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"code": "llm_timeout", "message": str(exc)},
        ) from exc

    return ChatResponse(
        conversation_id=payload.conversation_id,
        user_message=message_response(user_message),
        assistant_message=ChatAssistantMessageResponse(
            id=assistant_message.id,
            role="assistant",
            content=assistant_message.content_text,
            sources=sources,
        ),
        usage={},
    )


def parse_retrieval_scope(raw_scope: dict | None) -> RetrievalScope:
    if not raw_scope:
        return RetrievalScope()

    mode = raw_scope.get("mode", "all")
    category = raw_scope.get("category")
    language = raw_scope.get("language")
    raw_document_ids = raw_scope.get("document_ids") or raw_scope.get("selected_document_ids") or []

    if mode == "all":
        category = None
        raw_document_ids = []
    elif mode == "category":
        if not isinstance(category, str) or not category.strip():
            raise ValueError("Category scope requires a category.")
        raw_document_ids = []
    elif mode in {"documents", "selected_documents"}:
        if not isinstance(raw_document_ids, list) or not raw_document_ids:
            raise ValueError("Selected-document scope requires document_ids.")
        category = None
    else:
        raise ValueError(f"Unsupported retrieval scope mode: {mode}")

    if language is not None and not isinstance(language, str):
        raise ValueError("Scope language must be a string.")

    if not isinstance(raw_document_ids, list):
        raise ValueError("Scope document_ids must be a list.")

    return RetrievalScope(
        category=category.strip() if isinstance(category, str) else None,
        document_ids=tuple(str(document_id) for document_id in raw_document_ids),
        language=language.strip() if isinstance(language, str) and language.strip() else None,
    )


def sources_from_chunks(chunks: tuple[RetrievedChunk, ...]) -> list[dict]:
    return [
        {
            "document_id": chunk.document_id,
            "document_title": chunk.document_title,
            "document_version_id": chunk.document_version_id,
            "section_path": " > ".join(chunk.section_path),
            "snippet": chunk.chunk_text[:500],
            "score": chunk.score,
            "category": chunk.category,
            "chunk_id": chunk.chunk_id,
        }
        for chunk in chunks
    ]

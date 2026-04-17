from typing import Annotated

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

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def send_chat_message(
    payload: ChatRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    llm_gateway: Annotated[LlmGateway, Depends(get_generation_gateway)],
    embedding_service: Annotated[EmbeddingService, Depends(get_query_embedding_service)],
    vector_index: Annotated[VectorIndexService, Depends(get_retrieval_vector_index)],
) -> ChatResponse:
    conversation_service = ConversationService(db)
    settings = get_settings()
    try:
        conversation = conversation_service.get_conversation(
            user_id=current_user.id,
            conversation_id=payload.conversation_id,
        )
        if conversation.workspace_id != payload.workspace_id:
            raise ConversationAccessDenied("Conversation does not belong to the requested workspace.")

        retrieval_scope = parse_retrieval_scope(payload.scope if payload.scope is not None else conversation.selected_scope_json)
        retrieval = RetrievalService(
            session=db,
            embedding_service=embedding_service,
            vector_index=vector_index,
            settings=settings,
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
        memory = ConversationMemoryService(session=db, settings=settings).build_memory_package(
            user_id=current_user.id,
            workspace_id=payload.workspace_id,
            conversation_id=payload.conversation_id,
            exclude_message_ids={user_message.id},
        )
        prompt = PromptBuilder().build(
            PromptBuildInput(
                workspace_name=conversation.workspace.name if conversation.workspace else None,
                current_user_message=payload.message,
                memory=memory.prompt_memory,
                retrieved_chunks=retrieval.chunks,
            )
        )
        generation = llm_gateway.generate(GenerationRequest(messages=prompt.messages))
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
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_message", "message": str(exc)},
        ) from exc
    except DocumentAccessDenied as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_scope_filter", "message": str(exc)},
        ) from exc
    except (ConversationAccessDenied, WorkspaceAccessDenied) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "conversation_not_found", "message": str(exc)},
        ) from exc
    except OllamaGatewayError as exc:
        db.rollback()
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

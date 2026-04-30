import asyncio
from datetime import UTC, datetime
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user, get_db
from app.api.dependencies.llm import get_generation_gateway
from app.api.dependencies.retrieval import get_query_embedding_service, get_retrieval_vector_index
from app.api.routes.conversations import message_response
from app.api.schemas.conversations import ChatAssistantMessageResponse, ChatRequest, ChatResponse, CitationResponse
from app.core.config import get_settings
from app.core.config.routing_config import RoutingConfig
from app.domain.citations import CitationService
from app.domain.guardrails.service import GuardrailService
from app.domain.reranking.service import LocalCrossEncoderReranker, RerankingService, SimpleScoreReranker
from app.domain.embeddings import EmbeddingService
from app.domain.errors import ConversationAccessDenied, DocumentAccessDenied, WorkspaceAccessDenied
from app.domain.llm import GenerationRequest, LlmGateway
from app.domain.prompting import PromptBuilder, PromptBuildInput
from app.domain.routing.models import RequestContext, ResponseMode
from app.domain.routing.orchestrator import CapabilityOrchestrator
from app.domain.routing.router import RequestRouter
from app.domain.services.conversations import ConversationService
from app.domain.services.hybrid_retrieval import HybridRetrievalService
from app.domain.services.memory import ConversationMemoryService
from app.domain.services.retrieval import RetrievalScope, RetrievalService, RetrievedChunk, VectorIndexService
from app.domain.query_rewriting.service import QueryRewriteService
from app.domain.query_rewriting.models import QueryRewriteRequest, QueryRewriteMode
from app.domain.query_rewriting.multi_query_retrieval import MultiQueryRetrievalService
from app.domain.memory_context.contextualizer import ConversationContextualizer
from app.infrastructure.llm import OllamaGatewayError
from app.infrastructure.realtime import ChatProcessingEvent, chat_log_manager

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger(__name__)


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
    _loop = asyncio.get_event_loop()

    async def emit(category: str, stage: str, status: str, event_payload: dict[str, Any]) -> None:
        await chat_log_manager.publish(
            ChatProcessingEvent(
                conversation_id=payload.conversation_id,
                workspace_id=active_workspace_id,
                message_id=active_user_message_id,
                category=category,
                stage=stage,
                status=status,
                payload=safe_event_payload(event_payload),
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
            payload=safe_event_payload(event_payload),
            timestamp=datetime.now(UTC).isoformat(),
        )
        _loop.call_soon_threadsafe(_loop.create_task, chat_log_manager.publish(event))

    try:
        await emit(
            "request",
            "started",
            "started",
            {
                "message_length": len(payload.message),
                "scope": payload.scope,
            },
        )
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

        # ── Routing decision (E7) ────────────────────────────────────────
        routing_config = RoutingConfig()
        router = RequestRouter(classification_service=None, settings=routing_config)
        routing_context = RequestContext(
            query=payload.message,
            workspace_id=payload.workspace_id,
            conversation_id=payload.conversation_id,
        )
        routing_decision = router.route(routing_context)
        await emit(
            "routing",
            "decision_made",
            "completed",
            {
                "selected_mode": routing_decision.selected_mode.value,
                "router_strategy": routing_decision.router_strategy,
                "confidence": routing_decision.confidence,
            },
        )

        # ── Orchestration for refuse_out_of_scope mode (E7) ──────────────────────────
        # Short-circuit for refuse_out_of_scope without LLM call
        if routing_decision.selected_mode == ResponseMode.refuse_out_of_scope:
            orchestrator = CapabilityOrchestrator(
                retrieval_service=None,
                llm_gateway=None,
                memory_service=None,
                extraction_service=None,
                summarization_service=None,
                classification_service=None,
            )
            try:
                response_envelope = await orchestrator.execute(routing_decision, routing_context)
                await emit(
                    "orchestration",
                    "capability_executed",
                    "completed",
                    {
                        "response_mode": response_envelope.selected_mode.value,
                        "router_strategy": response_envelope.router_strategy,
                    },
                )

                # Create user message for the refusal response
                user_message = conversation_service.append_user_message(
                    user_id=current_user.id,
                    workspace_id=payload.workspace_id,
                    conversation_id=payload.conversation_id,
                    content=payload.message,
                )
                active_user_message_id = user_message.id

                assistant_message = conversation_service.append_assistant_message(
                    user_id=current_user.id,
                    workspace_id=payload.workspace_id,
                    conversation_id=payload.conversation_id,
                    content=response_envelope.content.get("message", "Request could not be processed."),
                    response_metadata={
                        "response_mode": response_envelope.selected_mode.value,
                        "router_reason": response_envelope.router_reason,
                        "router_strategy": response_envelope.router_strategy,
                        "sources": response_envelope.sources,
                    },
                )
                db.commit()
                await emit("request", "completed", "completed", {"assistant_message_id": assistant_message.id})

                return ChatResponse(
                    conversation_id=payload.conversation_id,
                    user_message=message_response(user_message),
                    assistant_message=ChatAssistantMessageResponse(
                        id=assistant_message.id,
                        role="assistant",
                        content=response_envelope.content.get("message", "Request could not be processed."),
                        sources=response_envelope.sources,
                        retrieved_sources=response_envelope.sources,
                        cited_sources=[],
                        response_mode=response_envelope.selected_mode.value,
                        guardrail_reason=response_envelope.router_reason,
                    ),
                    usage={},
                )
            except Exception as orch_exc:
                logger.exception(f"Orchestration failed for mode {routing_decision.selected_mode}: {orch_exc}")
                await emit("orchestration", "failed", "failed", {"error": str(orch_exc)})

        # ── Query Rewriting (E1) ────────────────────────────────────────
        # Build recent turns and summary early for query rewriting
        query_rewrite_cfg = settings.query_rewrite
        rewrite_plan = None

        if query_rewrite_cfg.query_rewrite_mode != "disabled":
            try:
                await emit("query_rewriting", "started", "started", {"mode": query_rewrite_cfg.query_rewrite_mode})

                # Extract recent messages and summary for query rewriting context
                recent_turns = []
                summary_text = None

                # Get recent messages from conversation
                recent_messages = conversation.messages
                if recent_messages:
                    # Filter and sort messages
                    user_assistant_messages = [
                        m for m in sorted(recent_messages, key=lambda x: x.created_at)
                        if m.role in {"user", "assistant"}
                    ]
                    # Get last N recent messages (excluding current one which hasn't been saved yet)
                    limit = min(settings.advanced_memory.memory_retrieval_recent_message_limit + 2, len(user_assistant_messages))
                    for msg in user_assistant_messages[-limit:]:
                        recent_turns.append({
                            "role": msg.role,
                            "content": msg.content_text,
                        })

                # Get summary if available
                if conversation.summary:
                    summary_text = conversation.summary.summary_text

                # Create contextualizer if memory contextualization is enabled
                contextualizer = None
                if settings.advanced_memory.memory_contextualization_enabled:
                    contextualizer = ConversationContextualizer(llm_gateway, settings.advanced_memory)

                # Execute query rewriting
                rewrite_service = QueryRewriteService(
                    llm=llm_gateway,
                    contextualizer=contextualizer,
                    settings=query_rewrite_cfg,
                )
                rewrite_plan = await rewrite_service.rewrite(
                    QueryRewriteRequest(
                        query=payload.message,
                        workspace_id=payload.workspace_id,
                        recent_turns=recent_turns,
                        summary=summary_text,
                    )
                )

                await emit(
                    "query_rewriting",
                    "completed",
                    "completed",
                    {
                        "mode": rewrite_plan.mode.value,
                        "was_contextualized": rewrite_plan.was_contextualized,
                        "rewrite_count": len(rewrite_plan.rewritten_queries),
                        "total_queries": len(rewrite_plan.all_queries),
                    },
                )
            except Exception as qr_exc:
                logger.warning(f"Query rewriting failed, falling back to original query: {qr_exc}")
                await emit("query_rewriting", "fallback", "failed", {"error": str(qr_exc)})

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
        await emit(
            "retrieval",
            "started",
            "started",
            {"query": payload.message, "mode": settings.hybrid_retrieval.mode},
        )

        # Use multi-query retrieval if query rewriting is enabled and multi_query mode is active
        use_multi_query = (
            rewrite_plan is not None
            and rewrite_plan.mode == QueryRewriteMode.MULTI_QUERY
        )

        if use_multi_query:
            # Multi-query retrieval using rewrite plan
            base_retrieval_service = RetrievalService(
                session=db,
                embedding_service=embedding_service,
                vector_index=vector_index,
                settings=settings,
                debug_hook=debug_hook,
            )
            multi_retrieval_service = MultiQueryRetrievalService(
                retrieval_service=base_retrieval_service,
                settings=settings.query_rewrite,
            )
            multi_result = multi_retrieval_service.retrieve(
                rewrite_plan=rewrite_plan,
                user_id=current_user.id,
                workspace_id=payload.workspace_id,
                scope=retrieval_scope,
            )

            # Convert dict result back to RetrievalResponse
            from app.domain.services.retrieval import RetrievalResponse as _RetrievalResponse

            def dict_to_chunk(chunk_dict):
                """Convert dict from multi-query retrieval back to RetrievedChunk."""
                if isinstance(chunk_dict, RetrievedChunk):
                    return chunk_dict
                # Ensure section_path is tuple
                section_path = chunk_dict.get("section_path", ())
                if isinstance(section_path, str):
                    section_path = (section_path,) if section_path else ()
                elif not isinstance(section_path, tuple):
                    section_path = tuple(section_path) if section_path else ()

                return RetrievedChunk(
                    chunk_id=chunk_dict.get("chunk_id", ""),
                    chunk_text=chunk_dict.get("chunk_text", ""),
                    document_id=chunk_dict.get("document_id", ""),
                    document_version_id=chunk_dict.get("document_version_id", ""),
                    document_title=chunk_dict.get("document_title", ""),
                    section_path=section_path,
                    score=chunk_dict.get("score", 0.0),
                    category=chunk_dict.get("category"),
                    language=chunk_dict.get("language"),
                    is_active=chunk_dict.get("is_active", True),
                    payload=chunk_dict.get("payload", {}),
                )

            retrieval = _RetrievalResponse(
                workspace_id=payload.workspace_id,
                query=payload.message,
                chunks=tuple(
                    dict_to_chunk(chunk)
                    for chunk in multi_result.get("chunks", [])
                ),
            )
        elif settings.hybrid_retrieval.mode == "hybrid":
            # Standard hybrid retrieval
            query_to_use = (
                rewrite_plan.all_queries[0] if rewrite_plan
                else payload.message
            )
            retrieval = HybridRetrievalService(
                session=db,
                embedding_service=embedding_service,
                vector_index=vector_index,
                settings=settings,
                debug_hook=debug_hook,
            ).retrieve(
                user_id=current_user.id,
                workspace_id=payload.workspace_id,
                query=query_to_use,
                scope=retrieval_scope,
            )
        else:
            # Standard vector-only retrieval
            query_to_use = (
                rewrite_plan.all_queries[0] if rewrite_plan
                else payload.message
            )
            retrieval = RetrievalService(
                session=db,
                embedding_service=embedding_service,
                vector_index=vector_index,
                settings=settings,
                debug_hook=debug_hook,
            ).retrieve(
                user_id=current_user.id,
                workspace_id=payload.workspace_id,
                query=query_to_use,
                scope=retrieval_scope,
            )
        user_message = conversation_service.append_user_message(
            user_id=current_user.id,
            workspace_id=payload.workspace_id,
            conversation_id=payload.conversation_id,
            content=payload.message,
        )
        active_user_message_id = user_message.id
        # ── Reranking (optional, after retrieval) ────────────────────────────
        rerank_cfg = settings.reranking
        if rerank_cfg.enabled:
            await emit("reranking", "started", "started", {"candidate_count": len(retrieval.chunks)})
            try:
                provider = LocalCrossEncoderReranker() if rerank_cfg.provider == "local_cross_encoder" else SimpleScoreReranker()
                reranker = RerankingService(
                    provider=provider,
                    enabled=True,
                    timeout_ms=rerank_cfg.timeout_ms,
                    fail_open=rerank_cfg.fail_open,
                    final_top_k=rerank_cfg.final_top_k,
                )
                reranked_chunks = tuple(reranker.rerank(payload.message, retrieval.chunks))
                from app.domain.services.retrieval import RetrievalResponse as _RetrievalResponse
                retrieval = _RetrievalResponse(
                    workspace_id=retrieval.workspace_id,
                    query=retrieval.query,
                    chunks=reranked_chunks,
                )
                await emit("reranking", "completed", "completed", {"final_count": len(reranked_chunks)})
            except Exception as _rerank_exc:
                await emit("reranking", "fallback", "failed", {"error": str(_rerank_exc)})

        await emit(
            "persistence",
            "user_message_saved",
            "completed",
            {"message_id": user_message.id, "content_length": len(user_message.content_text)},
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
                "recent_message_count": len(memory.prompt_memory.recent_messages),
                "has_summary": memory.prompt_memory.summary is not None,
            },
        )

        # ── Guardrails evaluation (A4) ────────────────────────────────────────
        guardrail_cfg = settings.guardrails
        guardrail_svc = GuardrailService(
            enabled=guardrail_cfg.enabled,
            in_scope_required=guardrail_cfg.in_scope_required,
            min_top_score=guardrail_cfg.min_top_score,
            min_usable_chunks=guardrail_cfg.min_usable_chunks,
            use_template_responses=guardrail_cfg.use_template_responses,
        )
        guardrail_decision = guardrail_svc.evaluate(
            query=payload.message,
            retrieved_chunks=retrieval.chunks,
        )
        await emit(
            "guardrails",
            "evaluated",
            "completed",
            {
                "response_mode": guardrail_decision.response_mode.value,
                "guardrail_reason": guardrail_decision.guardrail_reason,
            },
        )

        # For non-answer modes, short-circuit with template response (no LLM call)
        if not guardrail_decision.should_generate:
            template_text = guardrail_svc.get_template_response(guardrail_decision.response_mode) or ""
            assistant_message = conversation_service.append_assistant_message(
                user_id=current_user.id,
                workspace_id=payload.workspace_id,
                conversation_id=payload.conversation_id,
                content=template_text,
                response_metadata={
                    "response_mode": guardrail_decision.response_mode.value,
                    "guardrail_reason": guardrail_decision.guardrail_reason,
                    "sources": [],
                },
            )
            db.commit()
            await emit("request", "completed", "completed", {"assistant_message_id": assistant_message.id})

            # Return early with guardrail metadata and no citations
            return ChatResponse(
                conversation_id=payload.conversation_id,
                user_message=message_response(user_message),
                assistant_message=ChatAssistantMessageResponse(
                    id=assistant_message.id,
                    role="assistant",
                    content=template_text,
                    sources=[],
                    retrieved_sources=[],
                    cited_sources=[],
                    response_mode=guardrail_decision.response_mode.value,
                    guardrail_reason=guardrail_decision.guardrail_reason,
                ),
                usage={},
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
                "message_count": len(prompt.messages),
                "roles": [message.role for message in prompt.messages],
            },
        )
        generation = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: llm_gateway.generate(
                GenerationRequest(messages=prompt.messages, metadata={"debug_hook": debug_hook})
            ),
        )
        # Build normalized citation payload
        citation_svc = CitationService(
            max_exposed_citations=settings.citations.max_exposed_citations,
            excerpt_max_chars=settings.citations.excerpt_max_chars,
            include_retrieved_sources=settings.citations.include_retrieved_sources,
            include_cited_sources=settings.citations.include_cited_sources,
        )
        workspace_id_for_citations = payload.workspace_id
        retrieved_dtos = citation_svc.build_retrieved_sources(workspace_id_for_citations, retrieval.chunks)
        cited_dtos = citation_svc.select_cited_sources(workspace_id_for_citations, retrieval.chunks)

        # Legacy compatibility — keep `sources` field as flat list
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
                "response_mode": guardrail_decision.response_mode.value,
                "guardrail_reason": guardrail_decision.guardrail_reason,
                "citation_count": len(cited_dtos),
            },
        )
        await emit(
            "persistence",
            "assistant_message_saved",
            "completed",
            {
                "message_id": assistant_message.id,
                "content_length": len(assistant_message.content_text),
                "source_count": len(sources),
                "cited_source_count": len(cited_dtos),
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
    except Exception as exc:
        db.rollback()
        logger.exception("chat.request_failed conversation_id=%s workspace_id=%s", payload.conversation_id, active_workspace_id)
        await emit("error", "request_failed", "failed", {"code": "chat_failed", "error_type": type(exc).__name__})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "chat_failed", "message": "Chat request failed."},
        ) from exc

    def _dto_to_response(dto) -> CitationResponse:
        return CitationResponse(
            citation_id=dto.citation_id,
            workspace_id=dto.workspace_id,
            document_id=dto.document_id,
            document_version_id=dto.document_version_id,
            chunk_id=dto.chunk_id,
            chunk_index=dto.chunk_index,
            document_title=dto.document_title,
            heading=dto.heading,
            section_path=list(dto.section_path),
            excerpt=dto.excerpt,
            language=dto.language,
            retrieval_score=dto.retrieval_score,
            rank=dto.rank,
            category=dto.category,
            filename=dto.filename,
            storage_uri=dto.storage_uri,
            version_label=dto.version_label,
        )

    return ChatResponse(
        conversation_id=payload.conversation_id,
        user_message=message_response(user_message),
        assistant_message=ChatAssistantMessageResponse(
            id=assistant_message.id,
            role="assistant",
            content=assistant_message.content_text,
            sources=sources,
            retrieved_sources=[_dto_to_response(d) for d in retrieved_dtos] if settings.citations.include_retrieved_sources else [],
            cited_sources=[_dto_to_response(d) for d in cited_dtos] if settings.citations.include_cited_sources else [],
            response_mode=guardrail_decision.response_mode.value,
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


SENSITIVE_EVENT_KEYS = {"content", "message", "messages", "prompt", "query", "summary", "text", "text_preview"}


def safe_event_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: safe_event_value(key, value) for key, value in payload.items()}


def safe_event_value(key: str, value: Any) -> Any:
    if key in SENSITIVE_EVENT_KEYS:
        return redact_value(value)

    if isinstance(value, dict):
        return {nested_key: safe_event_value(nested_key, nested_value) for nested_key, nested_value in value.items()}

    if isinstance(value, list):
        return [safe_event_value(key, item) for item in value]

    return value


def redact_value(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        return {"redacted": True, "length": len(value)}
    if isinstance(value, list):
        return {"redacted": True, "count": len(value)}
    if isinstance(value, dict):
        return {"redacted": True, "keys": sorted(str(key) for key in value.keys())}
    return {"redacted": True}

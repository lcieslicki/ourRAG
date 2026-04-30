"""Capability orchestrator that executes routing decisions and builds responses."""

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from app.domain.routing.models import RequestContext, ResponseEnvelope, ResponseMode, RouteDecision

if TYPE_CHECKING:
    from app.domain.classification.service import ClassificationService
    from app.domain.extraction.service import ExtractionService
    from app.domain.llm import LlmGateway
    from app.domain.services.memory import ConversationMemoryService
    from app.domain.services.retrieval import RetrievalService, RetrievedChunk
    from app.domain.summarization.service import SummarizationService

logger = logging.getLogger(__name__)


class CapabilityOrchestrator:
    """Orchestrates the execution of capabilities based on routing decisions."""

    def __init__(
        self,
        retrieval_service: "RetrievalService | None" = None,
        llm_gateway: "LlmGateway | None" = None,
        memory_service: "ConversationMemoryService | None" = None,
        extraction_service: "ExtractionService | None" = None,
        summarization_service: "SummarizationService | None" = None,
        classification_service: "ClassificationService | None" = None,
    ) -> None:
        """Initialize the orchestrator with optional services.

        Args:
            retrieval_service: For QA mode retrieval.
            llm_gateway: For generation in QA, summarization, extraction modes.
            memory_service: For conversation context.
            extraction_service: For structured extraction mode.
            summarization_service: For summarization mode.
            classification_service: For query classification (used in router).
        """
        self.retrieval_service = retrieval_service
        self.llm_gateway = llm_gateway
        self.memory_service = memory_service
        self.extraction_service = extraction_service
        self.summarization_service = summarization_service
        self.classification_service = classification_service

    async def execute(
        self,
        route: RouteDecision,
        context: RequestContext,
    ) -> ResponseEnvelope:
        """Execute a capability based on the routing decision.

        Dispatches to appropriate capability handler based on selected_mode.
        Each handler builds a ResponseEnvelope with mode, reason, content, and sources.

        Args:
            route: The routing decision from RequestRouter.
            context: The request context with query, workspace, and metadata.

        Returns:
            ResponseEnvelope with capability output and metadata.
        """
        try:
            if route.selected_mode == ResponseMode.qa:
                return await self._execute_qa(route, context)
            elif route.selected_mode == ResponseMode.summarization:
                return await self._execute_summarization(route, context)
            elif route.selected_mode == ResponseMode.structured_extraction:
                return await self._execute_extraction(route, context)
            elif route.selected_mode == ResponseMode.admin_lookup:
                return await self._execute_admin_lookup(route, context)
            elif route.selected_mode == ResponseMode.refuse_out_of_scope:
                return await self._execute_refuse(route, context)
            else:
                # Fallback to QA for unknown modes
                logger.warning(f"Unknown response mode: {route.selected_mode}; falling back to QA")
                return await self._execute_qa(route, context)
        except Exception as e:
            logger.exception(f"Capability execution failed for mode {route.selected_mode}: {e}")
            # Return error response envelope
            return ResponseEnvelope(
                selected_mode=route.selected_mode,
                router_reason=route.router_reason,
                router_strategy=route.router_strategy,
                content={
                    "error": True,
                    "message": f"Execution failed: {str(e)}",
                },
                sources=[],
                debug_metadata={"error_type": type(e).__name__},
            )

    async def _execute_qa(
        self,
        route: RouteDecision,
        context: RequestContext,
    ) -> ResponseEnvelope:
        """Execute QA capability (retrieval + generation).

        This is a simplified QA executor that focuses on retrieving and
        packaging sources. The actual LLM generation happens upstream
        in the chat endpoint (this method prepares the foundation).

        Args:
            route: The routing decision.
            context: The request context.

        Returns:
            ResponseEnvelope with QA content and sources.
        """
        sources = []

        # Try to retrieve relevant documents if retrieval service is available
        if self.retrieval_service is not None:
            try:
                from app.domain.services.retrieval import RetrievalScope

                retrieval_response = self.retrieval_service.retrieve(
                    user_id=context.conversation_id or "unknown",
                    workspace_id=context.workspace_id,
                    query=context.query,
                    scope=RetrievalScope(),
                )
                sources = self._chunks_to_sources(retrieval_response.chunks)
            except Exception as e:
                logger.warning(f"QA retrieval failed: {e}")

        return ResponseEnvelope(
            selected_mode=ResponseMode.qa,
            router_reason=route.router_reason,
            router_strategy=route.router_strategy,
            content={
                "query": context.query,
                "message": "Ready for QA processing (retrieval and generation will proceed)",
            },
            sources=sources,
        )

    async def _execute_summarization(
        self,
        route: RouteDecision,
        context: RequestContext,
    ) -> ResponseEnvelope:
        """Execute summarization capability.

        Args:
            route: The routing decision.
            context: The request context.

        Returns:
            ResponseEnvelope with summarization content.
        """
        if self.summarization_service is None:
            return ResponseEnvelope(
                selected_mode=ResponseMode.summarization,
                router_reason=route.router_reason,
                router_strategy=route.router_strategy,
                content={
                    "error": True,
                    "message": "Summarization service is not available.",
                },
                sources=[],
            )

        try:
            from app.domain.summarization.models import SummaryFormat, SummarizationRequest, SummaryScope

            # Create a basic summarization request
            request = SummarizationRequest(
                workspace_id=context.workspace_id,
                format=SummaryFormat.plain_summary,
                scope=SummaryScope(use_retrieved_context=True),
                query=context.query,
            )

            # Get chunks to summarize (from retrieval if available)
            chunks = []
            if self.retrieval_service is not None:
                try:
                    from app.domain.services.retrieval import RetrievalScope

                    retrieval_response = self.retrieval_service.retrieve(
                        user_id=context.conversation_id or "unknown",
                        workspace_id=context.workspace_id,
                        query=context.query,
                        scope=RetrievalScope(),
                    )
                    chunks = [chunk.chunk_text for chunk in retrieval_response.chunks]
                except Exception as e:
                    logger.warning(f"Summarization retrieval failed: {e}")

            if not chunks:
                return ResponseEnvelope(
                    selected_mode=ResponseMode.summarization,
                    router_reason=route.router_reason,
                    router_strategy=route.router_strategy,
                    content={
                        "error": True,
                        "message": "No context available for summarization.",
                    },
                    sources=[],
                )

            result = self.summarization_service.summarize(request, chunks)

            return ResponseEnvelope(
                selected_mode=ResponseMode.summarization,
                router_reason=route.router_reason,
                router_strategy=route.router_strategy,
                content={
                    "summary": result.summary,
                    "format": result.format.value,
                    "scope": result.scope.dict(),
                },
                sources=result.sources,
            )
        except Exception as e:
            logger.exception(f"Summarization execution failed: {e}")
            return ResponseEnvelope(
                selected_mode=ResponseMode.summarization,
                router_reason=route.router_reason,
                router_strategy=route.router_strategy,
                content={
                    "error": True,
                    "message": f"Summarization failed: {str(e)}",
                },
                sources=[],
            )

    async def _execute_extraction(
        self,
        route: RouteDecision,
        context: RequestContext,
    ) -> ResponseEnvelope:
        """Execute structured extraction capability.

        Args:
            route: The routing decision.
            context: The request context.

        Returns:
            ResponseEnvelope with extraction content.
        """
        if self.extraction_service is None:
            return ResponseEnvelope(
                selected_mode=ResponseMode.structured_extraction,
                router_reason=route.router_reason,
                router_strategy=route.router_strategy,
                content={
                    "error": True,
                    "message": "Extraction service is not available.",
                },
                sources=[],
            )

        try:
            from app.domain.extraction.models import ExtractionMode, ExtractionRequest

            # Create extraction request (default schema: "default")
            request = ExtractionRequest(
                workspace_id=context.workspace_id,
                schema_name="default",
                mode=ExtractionMode.extract_from_retrieved_context,
                query=context.query,
            )

            result = await self.extraction_service.extract(request)

            return ResponseEnvelope(
                selected_mode=ResponseMode.structured_extraction,
                router_reason=route.router_reason,
                router_strategy=route.router_strategy,
                content={
                    "schema_name": result.schema_name,
                    "status": result.status.value,
                    "data": result.data or {},
                    "validation_errors": result.validation_errors,
                },
                sources=result.sources,
                debug_metadata=result.debug_metadata,
            )
        except Exception as e:
            logger.exception(f"Extraction execution failed: {e}")
            return ResponseEnvelope(
                selected_mode=ResponseMode.structured_extraction,
                router_reason=route.router_reason,
                router_strategy=route.router_strategy,
                content={
                    "error": True,
                    "message": f"Extraction failed: {str(e)}",
                },
                sources=[],
            )

    async def _execute_admin_lookup(
        self,
        route: RouteDecision,
        context: RequestContext,
    ) -> ResponseEnvelope:
        """Execute admin lookup capability (no LLM needed).

        Returns basic workspace/document information based on context.

        Args:
            route: The routing decision.
            context: The request context.

        Returns:
            ResponseEnvelope with admin lookup content.
        """
        return ResponseEnvelope(
            selected_mode=ResponseMode.admin_lookup,
            router_reason=route.router_reason,
            router_strategy=route.router_strategy,
            content={
                "workspace_id": context.workspace_id,
                "conversation_id": context.conversation_id,
                "lookup_query": context.query,
                "message": "Admin lookup executed; refer to workspace metadata.",
            },
            sources=[],
        )

    async def _execute_refuse(
        self,
        route: RouteDecision,
        context: RequestContext,
    ) -> ResponseEnvelope:
        """Execute refuse capability (out of scope response).

        Args:
            route: The routing decision.
            context: The request context.

        Returns:
            ResponseEnvelope with refusal message.
        """
        return ResponseEnvelope(
            selected_mode=ResponseMode.refuse_out_of_scope,
            router_reason=route.router_reason,
            router_strategy=route.router_strategy,
            content={
                "message": (
                    "I'm unable to help with this request as it falls outside my scope. "
                    "Please rephrase your question or contact support for assistance."
                ),
            },
            sources=[],
        )

    @staticmethod
    def _chunks_to_sources(chunks: tuple["RetrievedChunk", ...]) -> list[dict[str, Any]]:
        """Convert RetrievedChunk objects to source dictionaries.

        Args:
            chunks: Tuple of retrieved chunks.

        Returns:
            List of source dictionaries.
        """
        return [
            {
                "document_id": chunk.document_id,
                "document_title": chunk.document_title,
                "document_version_id": chunk.document_version_id,
                "section_path": " > ".join(chunk.section_path) if chunk.section_path else "",
                "snippet": chunk.chunk_text[:500],
                "score": chunk.score,
                "category": chunk.category,
                "chunk_id": chunk.chunk_id,
            }
            for chunk in chunks
        ]

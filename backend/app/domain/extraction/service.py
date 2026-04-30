import asyncio
import json
from typing import Any

from app.domain.extraction.models import ExtractionMode, ExtractionRequest, ExtractionResult, ExtractionStatus
from app.domain.extraction.prompt_builder import ExtractionPromptBuilder
from app.domain.extraction.schema_registry import ExtractionSchemaRegistry
from app.domain.llm import GenerationRequest, LlmGateway
from app.domain.prompting import PromptMessage


class ExtractionService:
    """Service for structured data extraction from documents."""

    def __init__(
        self,
        llm_gateway: LlmGateway,
        extraction_timeout_ms: int = 5000,
        validation_strict: bool = True,
    ) -> None:
        """
        Initialize the extraction service.

        Args:
            llm_gateway: LLM gateway for generation.
            extraction_timeout_ms: Timeout for extraction in milliseconds.
            validation_strict: Whether to enforce strict validation.
        """
        self.llm_gateway = llm_gateway
        self.timeout_seconds = extraction_timeout_ms / 1000.0
        self.validation_strict = validation_strict

    async def extract(self, request: ExtractionRequest, context_chunks: list[str] | None = None) -> ExtractionResult:
        """
        Extract structured data based on the request.

        Args:
            request: The extraction request.

        Returns:
            The extraction result.
        """
        try:
            schema = ExtractionSchemaRegistry.get(request.schema_name)
        except KeyError as e:
            return ExtractionResult(
                schema_name=request.schema_name,
                status=ExtractionStatus.validation_failure,
                validation_errors=[str(e)],
            )

        chunks = context_chunks or self._get_context_chunks(request)

        if not chunks:
            return ExtractionResult(
                schema_name=request.schema_name,
                status=ExtractionStatus.no_context,
            )

        prompt = ExtractionPromptBuilder.build_extraction_prompt(
            schema=schema,
            context_chunks=chunks,
            schema_name=request.schema_name,
        )

        try:
            response_text = await asyncio.wait_for(
                self._call_llm(prompt),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            return ExtractionResult(
                schema_name=request.schema_name,
                status=ExtractionStatus.timeout,
            )

        try:
            extracted_data = self._parse_json_response(response_text)
        except ValueError as e:
            return ExtractionResult(
                schema_name=request.schema_name,
                status=ExtractionStatus.validation_failure,
                validation_errors=[f"Failed to parse LLM response: {str(e)}"],
            )

        is_valid, errors = ExtractionSchemaRegistry.validate(request.schema_name, extracted_data)

        if not is_valid:
            return ExtractionResult(
                schema_name=request.schema_name,
                status=ExtractionStatus.validation_failure,
                validation_errors=errors,
                data=extracted_data if not self.validation_strict else None,
            )

        return ExtractionResult(
            schema_name=request.schema_name,
            status=ExtractionStatus.success,
            data=extracted_data,
            sources=self._build_sources(chunks),
        )

    async def _call_llm(self, prompt: str) -> str:
        """
        Call the LLM gateway synchronously but wrapped for async context.

        Args:
            prompt: The extraction prompt.

        Returns:
            The LLM response text.
        """
        request = GenerationRequest(
            messages=(PromptMessage(role="user", content=prompt),),
        )

        response = self.llm_gateway.generate(request)
        return response.text

    def _get_context_chunks(self, request: ExtractionRequest) -> list[str]:
        """
        Get context chunks based on extraction mode.

        Args:
            request: The extraction request.

        Returns:
            List of context chunk strings.
        """
        if request.mode == ExtractionMode.extract_from_selected_documents:
            return [f"[Document {doc_id}]" for doc_id in request.document_ids]
        elif request.mode == ExtractionMode.extract_from_retrieved_context:
            if request.query:
                return [f"Retrieved context for query: {request.query}"]
            return []
        return []

    def _parse_json_response(self, response_text: str) -> dict[str, Any]:
        """
        Parse JSON from LLM response.

        Args:
            response_text: The LLM response text.

        Returns:
            Parsed JSON as dictionary.

        Raises:
            ValueError: If JSON parsing fails.
        """
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        return json.loads(text)

    def _build_sources(self, context_chunks: list[str]) -> list[dict]:
        """
        Build source attribution list.

        Args:
            context_chunks: The context chunks used for extraction.

        Returns:
            List of source dictionaries.
        """
        return [{"text": chunk[:100], "type": "document"} for chunk in context_chunks]

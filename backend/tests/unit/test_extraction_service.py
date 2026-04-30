import asyncio
import pytest
from unittest.mock import MagicMock

from app.domain.extraction.models import ExtractionMode, ExtractionStatus
from app.domain.extraction.schema_registry import ExtractionSchemaRegistry
from app.domain.extraction.service import ExtractionService
from app.domain.llm import GenerationRequest, GenerationResponse
from app.domain.extraction.prompt_builder import ExtractionPromptBuilder


class TestSchemaRegistry:
    """Tests for ExtractionSchemaRegistry."""

    def test_schema_registry_returns_known_schema(self):
        """Test that known schemas can be retrieved."""
        schema = ExtractionSchemaRegistry.get("procedure_metadata_v1")
        assert schema is not None
        assert "properties" in schema
        assert "required" in schema
        assert "title" in schema["properties"]

    def test_schema_registry_raises_on_unknown(self):
        """Test that unknown schema raises KeyError."""
        with pytest.raises(KeyError):
            ExtractionSchemaRegistry.get("nonexistent_schema")

    def test_validation_success_with_complete_data(self):
        """Test successful validation with complete data."""
        data = {
            "title": "Test Procedure",
            "owner": "John Doe",
            "department": "HR",
        }
        is_valid, errors = ExtractionSchemaRegistry.validate("procedure_metadata_v1", data)
        assert is_valid is True
        assert errors == []

    def test_validation_failure_missing_required_field(self):
        """Test validation failure when required field is missing."""
        data = {
            "title": "Test Procedure",
            "owner": "John Doe",
        }
        is_valid, errors = ExtractionSchemaRegistry.validate("procedure_metadata_v1", data)
        assert is_valid is False
        assert len(errors) > 0


class TestPromptBuilder:
    """Tests for ExtractionPromptBuilder."""

    def test_prompt_builder_includes_schema_name(self):
        """Test that built prompt includes the schema name."""
        schema = ExtractionSchemaRegistry.get("document_brief_v1")
        context_chunks = ["This is a test document about procedures."]

        prompt = ExtractionPromptBuilder.build_extraction_prompt(
            schema=schema,
            context_chunks=context_chunks,
            schema_name="document_brief_v1",
        )

        assert "document_brief_v1" in prompt
        assert "Schema:" in prompt
        assert "Document Context:" in prompt


class TestExtractionResult:
    """Tests for ExtractionResult envelope."""

    def test_extraction_result_envelope_shape(self):
        """Test that extraction result has correct shape."""
        from app.domain.extraction.models import ExtractionResult

        result = ExtractionResult(
            mode="structured_extraction",
            schema_name="procedure_metadata_v1",
            status=ExtractionStatus.success,
            data={"title": "Test", "owner": "Owner", "department": "Dept"},
            sources=[{"text": "chunk", "type": "document"}],
        )

        assert result.mode == "structured_extraction"
        assert result.schema_name == "procedure_metadata_v1"
        assert result.status == ExtractionStatus.success
        assert result.data is not None
        assert len(result.sources) > 0


class TestExtractionService:
    """Tests for ExtractionService."""

    def test_service_returns_validation_failure_on_bad_schema(self):
        """Test that service returns validation failure for unknown schema."""
        mock_gateway = MagicMock()
        service = ExtractionService(llm_gateway=mock_gateway)

        from app.domain.extraction.models import ExtractionRequest
        request = ExtractionRequest(
            workspace_id="ws-1",
            schema_name="unknown_schema",
            mode=ExtractionMode.extract_from_selected_documents,
            document_ids=["doc-1"],
        )

        result = asyncio.run(service.extract(request))
        assert result.status == ExtractionStatus.validation_failure

    def test_service_returns_no_context_on_empty_chunks(self):
        """Test that service returns no_context when no chunks are available."""
        mock_gateway = MagicMock()
        service = ExtractionService(llm_gateway=mock_gateway)

        from app.domain.extraction.models import ExtractionRequest
        request = ExtractionRequest(
            workspace_id="ws-1",
            schema_name="procedure_metadata_v1",
            mode=ExtractionMode.extract_from_retrieved_context,
            query=None,
        )

        result = asyncio.run(service.extract(request))
        assert result.status == ExtractionStatus.no_context

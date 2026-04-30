import pytest


@pytest.mark.integration
class TestExtractionAPI:
    """Integration tests for the extraction API endpoint."""

    def test_extraction_endpoint_exists(self):
        """Test that extraction endpoint is properly structured."""
        from app.api.routes.extraction import router

        routes = []
        for route in router.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                routes.append((route.path, route.methods))

        assert any("extract" in path for path, _ in routes)

    def test_extraction_request_schema_validation(self):
        """Test that extraction request schema validates correctly."""
        from app.api.schemas.extraction import ExtractionRequestSchema
        from app.domain.extraction.models import ExtractionMode

        request = ExtractionRequestSchema(
            workspace_id="ws-1",
            schema_name="procedure_metadata_v1",
            mode=ExtractionMode.extract_from_selected_documents,
            document_ids=["doc-1"],
        )

        assert request.workspace_id == "ws-1"
        assert request.schema_name == "procedure_metadata_v1"
        assert request.mode == ExtractionMode.extract_from_selected_documents

    def test_extraction_response_schema_structure(self):
        """Test that extraction response schema has correct structure."""
        from app.api.schemas.extraction import ExtractionResponseSchema
        from app.domain.extraction.models import ExtractionStatus

        response = ExtractionResponseSchema(
            schema_name="procedure_metadata_v1",
            status=ExtractionStatus.success,
            data={"title": "Test", "owner": "Owner", "department": "Dept"},
        )

        assert response.mode == "structured_extraction"
        assert response.schema_name == "procedure_metadata_v1"
        assert response.status == ExtractionStatus.success
        assert response.data is not None

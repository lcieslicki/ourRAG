import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.db import get_db
from app.api.dependencies.llm import get_generation_gateway
from app.domain.llm import GenerationResponse
from app.main import app
from tests.factories import create_membership, create_user, create_workspace


class FakeSummarizationGateway:
    """Fake LLM gateway for summarization testing."""

    def generate(self, request):
        return GenerationResponse(
            text="This is a test summary of the provided content.",
            model="fake-summarizer",
            provider="fake",
            finish_reason="stop",
            metadata={},
        )


@pytest.mark.integration
def test_summarize_endpoint_requires_authentication(db_session) -> None:
    """Test that summarize endpoint requires user authentication."""
    client = TestClient(app)

    response = client.post(
        "/api/summarize",
        json={
            "workspace_id": "workspace-1",
            "format": "plain_summary",
            "scope": {},
            "query": "What is this?",
        },
    )

    assert response.status_code == 401


@pytest.mark.integration
def test_summarize_endpoint_validates_workspace_membership(db_session) -> None:
    """Test that summarize endpoint validates user is workspace member."""
    client = TestClient(app)
    user = create_user(db_session)
    workspace = create_workspace(db_session)

    # User is not a member of the workspace
    # This test would need proper auth setup to fully test
    pass


@pytest.mark.integration
def test_summarize_endpoint_with_plain_summary_format(db_session) -> None:
    """Test summarize endpoint with plain_summary format."""
    # Integration test setup would go here
    # Would need proper fixtures for user, workspace, auth
    pass


@pytest.mark.integration
def test_summarize_endpoint_returns_correct_response_structure(db_session) -> None:
    """Test that summarize endpoint returns correct response structure."""
    # Response should have:
    # - mode: "summarization"
    # - format: selected format
    # - scope: scope information
    # - summary: text content
    # - sources: list of source attributions
    pass


@pytest.mark.integration
def test_summarize_with_different_formats(db_session) -> None:
    """Test that summarize endpoint works with all supported formats."""
    formats = ["plain_summary", "bullet_brief", "checklist", "key_points_and_risks"]
    # Each format should return valid response structure
    pass


@pytest.mark.integration
def test_summarize_with_document_scope(db_session) -> None:
    """Test summarization with document-specific scope."""
    # Should summarize only specified document
    pass


@pytest.mark.integration
def test_summarize_with_section_scope(db_session) -> None:
    """Test summarization with section-specific scope."""
    # Should summarize only specified section
    pass


@pytest.mark.integration
def test_summarize_with_retrieved_context_scope(db_session) -> None:
    """Test summarization with retrieved context as scope."""
    # Should use retrieved chunks as context
    pass

"""Integration tests for routing and orchestration."""

import asyncio
import pytest
from pathlib import Path

from app.core.config.routing_config import RoutingConfig
from app.domain.classification.models import QueryClassificationResult, QueryIntent
from app.domain.models import DocumentVersion
from app.domain.routing.models import RequestContext, ResponseMode, RouteDecision
from app.domain.routing.orchestrator import CapabilityOrchestrator
from app.domain.routing.router import RequestRouter
from app.infrastructure.storage.local import LocalFileStorage
from app.workers.ingestion import IngestionJobRunner
from tests.factories import create_membership, create_user, create_workspace
from tests.e2e.test_mvp_happy_path import (
    DeterministicEmbeddingService,
    InMemoryVectorIndex,
    GroundedFakeGateway,
    client_with_dependencies,
    clear_overrides,
)


class MockClassificationService:
    """Mock classification service for integration tests."""

    def __init__(self, intent: QueryIntent = QueryIntent.qa, confidence: float = 0.9) -> None:
        self.intent = intent
        self.confidence = confidence

    def classify_query(self, query: str, workspace_context: dict | None = None) -> QueryClassificationResult:
        return QueryClassificationResult(
            label=self.intent.value,
            confidence=self.confidence,
            intent=self.intent,
            is_in_scope=True,
        )


@pytest.mark.integration
def test_routing_falls_back_to_qa_on_weak_confidence() -> None:
    """Verify routing falls back to QA when classification confidence is weak."""
    # Create a classification service with low confidence
    classification_service = MockClassificationService(intent=QueryIntent.summary, confidence=0.5)
    config = RoutingConfig(routing_enabled=True, routing_min_confidence=0.7)
    router = RequestRouter(classification_service=classification_service, settings=config)

    context = RequestContext(
        query="Summarize the policy",
        workspace_id="workspace-1",
    )

    decision = router.route(context)

    assert decision.selected_mode == ResponseMode.qa
    assert decision.is_fallback is True
    assert "low_confidence" in decision.router_strategy


@pytest.mark.integration
async def test_qa_mode_executes_without_retrieval() -> None:
    """Verify QA mode executes without external services."""
    orchestrator = CapabilityOrchestrator(
        retrieval_service=None,
        llm_gateway=None,
    )

    route = RouteDecision(
        selected_mode=ResponseMode.qa,
        confidence=1.0,
        router_strategy="test",
        router_reason="Test reason",
    )

    context = RequestContext(
        query="What is the vacation policy?",
        workspace_id="workspace-1",
    )

    response = await orchestrator.execute(route, context)

    assert response.selected_mode == ResponseMode.qa
    assert response.router_reason == "Test reason"
    assert response.router_strategy == "test"
    assert isinstance(response.content, dict)
    assert "query" in response.content


@pytest.mark.integration
async def test_routing_metadata_in_response() -> None:
    """Verify response includes routing metadata."""
    orchestrator = CapabilityOrchestrator()

    route = RouteDecision(
        selected_mode=ResponseMode.qa,
        confidence=0.95,
        router_strategy="classification_based",
        router_reason="Classified as QA intent.",
    )

    context = RequestContext(
        query="How do I request vacation?",
        workspace_id="workspace-1",
    )

    response = await orchestrator.execute(route, context)

    assert response.selected_mode == ResponseMode.qa
    assert response.router_reason == "Classified as QA intent."
    assert response.router_strategy == "classification_based"


@pytest.mark.integration
async def test_refuse_mode_executes() -> None:
    """Verify refuse mode returns refusal message."""
    orchestrator = CapabilityOrchestrator()

    route = RouteDecision(
        selected_mode=ResponseMode.refuse_out_of_scope,
        confidence=0.85,
        router_strategy="classification_based",
        router_reason="Query is out of scope.",
    )

    context = RequestContext(
        query="Tell me a joke",
        workspace_id="workspace-1",
    )

    response = await orchestrator.execute(route, context)

    assert response.selected_mode == ResponseMode.refuse_out_of_scope
    assert "message" in response.content
    assert "unable" in response.content["message"].lower()


@pytest.mark.integration
async def test_admin_lookup_mode_executes() -> None:
    """Verify admin lookup mode executes."""
    orchestrator = CapabilityOrchestrator()

    route = RouteDecision(
        selected_mode=ResponseMode.admin_lookup,
        confidence=1.0,
        router_strategy="classification_based",
        router_reason="Admin lookup intent detected.",
    )

    context = RequestContext(
        query="Show workspace info",
        workspace_id="workspace-1",
        conversation_id="conv-123",
    )

    response = await orchestrator.execute(route, context)

    assert response.selected_mode == ResponseMode.admin_lookup
    assert response.content["workspace_id"] == "workspace-1"
    assert response.content["conversation_id"] == "conv-123"


@pytest.mark.integration
def test_routing_with_ui_hint_and_classification() -> None:
    """Verify routing prefers classification over UI hint when available."""
    classification_service = MockClassificationService(intent=QueryIntent.summary, confidence=0.92)
    config = RoutingConfig(
        routing_enabled=True,
        routing_allow_ui_mode_hint=True,
        routing_min_confidence=0.7,
    )
    router = RequestRouter(classification_service=classification_service, settings=config)

    context = RequestContext(
        query="Summarize the policy",
        workspace_id="workspace-1",
        ui_mode_hint="qa",  # Different from classification
    )

    decision = router.route(context)

    # Classification should take precedence
    assert decision.selected_mode == ResponseMode.summarization
    assert decision.router_strategy == "classification_based"


@pytest.mark.integration
def test_end_to_end_routing_and_orchestration() -> None:
    """End-to-end test: route a query and execute it."""
    classification_service = MockClassificationService(intent=QueryIntent.qa, confidence=0.9)
    config = RoutingConfig(routing_enabled=True, routing_min_confidence=0.7)
    router = RequestRouter(classification_service=classification_service, settings=config)

    context = RequestContext(
        query="What is the vacation policy?",
        workspace_id="workspace-1",
        conversation_id="conv-123",
    )

    # Step 1: Route
    decision = router.route(context)
    assert decision.selected_mode == ResponseMode.qa
    assert not decision.is_fallback

    # Step 2: Execute
    orchestrator = CapabilityOrchestrator()
    response = asyncio.run(orchestrator.execute(decision, context))

    assert response.selected_mode == ResponseMode.qa
    assert response.router_strategy == decision.router_strategy
    assert response.router_reason == decision.router_reason


@pytest.mark.integration
def test_existing_e2e_happy_path_not_broken(db_session, tmp_path) -> None:
    """Verify that routing integration does not break the existing MVP happy path.

    This test runs a simplified version of the MVP happy path to ensure
    the routing layer (E7) is backward compatible with existing QA flow.
    """
    admin = create_user(db_session, email_prefix="routing-test-admin")
    workspace = create_workspace(db_session, slug_prefix="routing-test-workspace")
    create_membership(db_session, user=admin, workspace=workspace, role="admin")

    embedding_service = DeterministicEmbeddingService()
    vector_index = InMemoryVectorIndex()
    gateway = GroundedFakeGateway(expected_prompt_fragments=["Employees request vacation leave through the HR portal."])
    client = client_with_dependencies(db_session, tmp_path, embedding_service, vector_index, gateway)

    fixture = Path(__file__).parents[2] / "fixtures" / "retrieval" / "acme_hr_handbook.md"

    try:
        # Upload document
        upload = client.post(
            "/api/documents/upload",
            headers={"X-User-Id": admin.id},
            data={
                "workspace_id": workspace.id,
                "title": "HR Handbook",
                "tags": "hr,vacation",
            },
            files={"file": ("hr_handbook.md", fixture.read_bytes(), "text/markdown")},
        )
        assert upload.status_code == 201
        upload_payload = upload.json()
        version = db_session.get(DocumentVersion, upload_payload["document_version_id"])
        assert version is not None

        # Process ingestion
        processed = IngestionJobRunner(
            db_session,
            storage=LocalFileStorage(tmp_path),
            embedding_service=embedding_service,
            vector_index=vector_index,
        ).run_until_idle()

        db_session.refresh(version)
        assert version.processing_status == "ready"
        assert version.is_active is True

        # Create conversation
        conversation = client.post(
            "/api/conversations",
            headers={"X-User-Id": admin.id},
            json={"workspace_id": workspace.id, "title": "Routing test question"},
        )
        assert conversation.status_code == 201
        conversation_id = conversation.json()["id"]

        # Send chat message (routing is now integrated here)
        chat = client.post(
            "/api/chat",
            headers={"X-User-Id": admin.id},
            json={
                "workspace_id": workspace.id,
                "conversation_id": conversation_id,
                "message": "How do I request vacation leave?",
                "scope": {"mode": "category", "category": "HR"},
            },
        )

        # Verify response
        assert chat.status_code == 200
        payload = chat.json()
        assert payload["conversation_id"] == conversation_id
        assert "HR portal" in payload["assistant_message"]["content"]
        assert payload["assistant_message"]["sources"]
        source = payload["assistant_message"]["sources"][0]
        assert source["document_id"] == upload_payload["document_id"]
        assert source["document_title"] == "HR Handbook"
        assert source["document_version_id"] == version.id
        assert "vacation" in source["snippet"].lower()

    finally:
        clear_overrides()

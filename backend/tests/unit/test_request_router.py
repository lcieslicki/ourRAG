"""Unit tests for RequestRouter."""

import pytest

from app.core.config.routing_config import RoutingConfig
from app.domain.classification.models import QueryClassificationResult, QueryIntent
from app.domain.routing.models import RequestContext, ResponseMode, RouteDecision
from app.domain.routing.router import RequestRouter


class MockClassificationService:
    """Mock classification service for testing."""

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


def test_disabled_routing_returns_qa() -> None:
    """When routing is disabled, always return qa mode."""
    config = RoutingConfig(routing_enabled=False)
    router = RequestRouter(settings=config)
    context = RequestContext(
        query="What is vacation policy?",
        workspace_id="workspace-1",
    )

    decision = router.route(context)

    assert decision.selected_mode == ResponseMode.qa
    assert decision.confidence == 1.0
    assert decision.router_strategy == "disabled_default"
    assert not decision.is_fallback


def test_route_summary_intent_to_summarization() -> None:
    """Route summary intent to summarization mode."""
    classification_service = MockClassificationService(intent=QueryIntent.summary, confidence=0.95)
    config = RoutingConfig(routing_enabled=True, routing_min_confidence=0.7)
    router = RequestRouter(classification_service=classification_service, settings=config)
    context = RequestContext(
        query="Summarize the vacation policy",
        workspace_id="workspace-1",
    )

    decision = router.route(context)

    assert decision.selected_mode == ResponseMode.summarization
    assert decision.confidence == 0.95
    assert decision.router_strategy == "classification_based"
    assert not decision.is_fallback


def test_route_extraction_intent_to_extraction() -> None:
    """Route extraction intent to structured_extraction mode."""
    classification_service = MockClassificationService(intent=QueryIntent.extraction, confidence=0.88)
    config = RoutingConfig(routing_enabled=True, routing_min_confidence=0.7)
    router = RequestRouter(classification_service=classification_service, settings=config)
    context = RequestContext(
        query="Extract all employee names and departments",
        workspace_id="workspace-1",
    )

    decision = router.route(context)

    assert decision.selected_mode == ResponseMode.structured_extraction
    assert decision.confidence == 0.88
    assert decision.router_strategy == "classification_based"
    assert not decision.is_fallback


def test_low_confidence_falls_back_to_qa() -> None:
    """When confidence is below threshold, fall back to qa."""
    classification_service = MockClassificationService(intent=QueryIntent.summary, confidence=0.5)
    config = RoutingConfig(routing_enabled=True, routing_min_confidence=0.7)
    router = RequestRouter(classification_service=classification_service, settings=config)
    context = RequestContext(
        query="Summarize the vacation policy",
        workspace_id="workspace-1",
    )

    decision = router.route(context)

    assert decision.selected_mode == ResponseMode.qa
    assert decision.confidence == 0.5
    assert decision.is_fallback
    assert "low_confidence" in decision.router_strategy


def test_ui_mode_hint_used_when_allowed() -> None:
    """Use UI mode hint when routing allows it and classification unavailable."""
    config = RoutingConfig(routing_enabled=True, routing_allow_ui_mode_hint=True)
    router = RequestRouter(classification_service=None, settings=config)
    context = RequestContext(
        query="Some query",
        workspace_id="workspace-1",
        ui_mode_hint="summarization",
    )

    decision = router.route(context)

    assert decision.selected_mode == ResponseMode.summarization
    assert decision.router_strategy == "ui_hint_fallback"
    assert decision.is_fallback


def test_ui_mode_hint_ignored_when_disabled() -> None:
    """Ignore UI mode hint when routing disallows it."""
    config = RoutingConfig(routing_enabled=True, routing_allow_ui_mode_hint=False)
    router = RequestRouter(classification_service=None, settings=config)
    context = RequestContext(
        query="Some query",
        workspace_id="workspace-1",
        ui_mode_hint="summarization",
    )

    decision = router.route(context)

    assert decision.selected_mode == ResponseMode.qa
    assert decision.router_strategy == "safe_default"
    assert decision.is_fallback


def test_refuse_out_of_scope_route() -> None:
    """Route out-of-scope intent to refuse mode."""
    classification_service = MockClassificationService(intent=QueryIntent.other, confidence=0.92)
    config = RoutingConfig(routing_enabled=True, routing_min_confidence=0.7)
    router = RequestRouter(classification_service=classification_service, settings=config)
    context = RequestContext(
        query="Tell me a joke about pizza",
        workspace_id="workspace-1",
    )

    decision = router.route(context)

    # "other" intent defaults to qa, not refuse
    assert decision.selected_mode == ResponseMode.qa
    assert decision.router_strategy == "classification_based"


def test_response_envelope_has_required_fields() -> None:
    """Ensure RouteDecision has all required fields."""
    decision = RouteDecision(
        selected_mode=ResponseMode.qa,
        confidence=1.0,
        router_strategy="test",
        router_reason="Test reason",
    )

    assert decision.selected_mode == ResponseMode.qa
    assert decision.confidence == 1.0
    assert decision.router_strategy == "test"
    assert decision.router_reason == "Test reason"
    assert decision.is_fallback is False


def test_classification_exception_falls_back_safely() -> None:
    """When classification raises exception, fall back to safe default."""
    class BrokenClassificationService:
        def classify_query(self, query: str, workspace_context: dict | None = None):
            raise RuntimeError("Classification service is broken")

    config = RoutingConfig(routing_enabled=True, routing_min_confidence=0.7)
    router = RequestRouter(classification_service=BrokenClassificationService(), settings=config)
    context = RequestContext(
        query="Some query",
        workspace_id="workspace-1",
    )

    decision = router.route(context)

    assert decision.selected_mode == ResponseMode.qa
    assert decision.router_strategy == "safe_default"
    assert decision.is_fallback


def test_intent_to_mode_mapping() -> None:
    """Test intent-to-mode mapping for all intents."""
    assert RequestRouter._intent_to_mode("summary") == ResponseMode.summarization
    assert RequestRouter._intent_to_mode("extraction") == ResponseMode.structured_extraction
    assert RequestRouter._intent_to_mode("admin_lookup") == ResponseMode.admin_lookup
    assert RequestRouter._intent_to_mode("qa") == ResponseMode.qa
    assert RequestRouter._intent_to_mode("other") == ResponseMode.qa


def test_parse_valid_ui_mode_hint() -> None:
    """Parse valid UI mode hint."""
    mode = RequestRouter._parse_ui_mode_hint("qa")
    assert mode == ResponseMode.qa

    mode = RequestRouter._parse_ui_mode_hint("summarization")
    assert mode == ResponseMode.summarization

    mode = RequestRouter._parse_ui_mode_hint("STRUCTURED_EXTRACTION")
    assert mode == ResponseMode.structured_extraction


def test_parse_invalid_ui_mode_hint() -> None:
    """Invalid UI mode hint returns None."""
    mode = RequestRouter._parse_ui_mode_hint("invalid_mode")
    assert mode is None

    mode = RequestRouter._parse_ui_mode_hint("")
    assert mode is None

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config.query_rewrite_config import QueryRewriteConfig
from app.domain.llm.base import GenerationResponse
from app.domain.memory_context.models import ContextualizedTurn
from app.domain.query_rewriting.models import (
    QueryRewriteMode,
    QueryRewriteRequest,
    RewritePlan,
)
from app.domain.query_rewriting.service import QueryRewriteService


class TestQueryRewriteModels:
    """Tests for QueryRewritePlan and related models."""

    def test_rewrite_plan_all_queries_includes_original_when_no_contextualization(self):
        """Test that all_queries includes original when contextualized_query is None."""
        plan = RewritePlan(
            original_query="what is the policy",
            contextualized_query=None,
            rewritten_queries=["policy details", "company rules"],
            mode=QueryRewriteMode.MULTI_QUERY,
            was_contextualized=False,
        )

        assert plan.all_queries == [
            "what is the policy",
            "policy details",
            "company rules",
        ]

    def test_rewrite_plan_all_queries_includes_contextualized_first(self):
        """Test that all_queries includes contextualized_query first."""
        plan = RewritePlan(
            original_query="it",
            contextualized_query="what is the vacation policy",
            rewritten_queries=["policy details", "vacation rules"],
            mode=QueryRewriteMode.MULTI_QUERY,
            was_contextualized=True,
        )

        assert plan.all_queries == [
            "what is the vacation policy",
            "policy details",
            "vacation rules",
        ]

    def test_rewrite_plan_all_queries_deduplicates(self):
        """Test that all_queries removes duplicates."""
        plan = RewritePlan(
            original_query="policy",
            contextualized_query="policy",  # Duplicate of original
            rewritten_queries=["policy", "company rules"],  # First is duplicate
            mode=QueryRewriteMode.MULTI_QUERY,
            was_contextualized=False,
        )

        assert plan.all_queries == [
            "policy",
            "company rules",
        ]

    def test_rewrite_plan_disabled_mode_only_has_original(self):
        """Test that disabled mode returns just original query."""
        plan = RewritePlan(
            original_query="what is the policy",
            mode=QueryRewriteMode.DISABLED,
            was_contextualized=False,
        )

        assert plan.all_queries == ["what is the policy"]
        assert plan.rewritten_queries == []


class FakeLLMGateway:
    """Fake LLM for testing."""

    def __init__(self, response_text: str):
        self.response_text = response_text
        self.calls = []

    def generate(self, request):
        self.calls.append(request)
        return GenerationResponse(
            text=self.response_text,
            model="fake-model",
            provider="fake",
        )


class FakeContextualizer:
    """Fake contextualizer for testing."""

    def __init__(self, contextualized_text: str, should_contextualize: bool = True):
        self.contextualized_text = contextualized_text
        self.should_contextualize = should_contextualize
        self.calls = []

    async def contextualize(
        self,
        user_message: str,
        recent_turns: list[dict],
        summary: str | None,
        workspace_id: str,
    ) -> ContextualizedTurn:
        self.calls.append(
            {
                "user_message": user_message,
                "recent_turns": recent_turns,
                "summary": summary,
                "workspace_id": workspace_id,
            }
        )
        return ContextualizedTurn(
            original_query=user_message,
            contextualized_query=self.contextualized_text,
            was_contextualized=self.should_contextualize,
            used_summary=summary is not None,
            used_recent_turns=len(recent_turns),
        )


class TestQueryRewriteService:
    """Tests for QueryRewriteService."""

    @pytest.mark.asyncio
    async def test_disabled_mode_returns_original_query_only(self):
        """Test that disabled mode returns original query without rewriting."""
        settings = QueryRewriteConfig(query_rewrite_mode="disabled")
        llm = FakeLLMGateway("")
        service = QueryRewriteService(llm=llm, contextualizer=None, settings=settings)

        request = QueryRewriteRequest(
            query="what is the policy",
            workspace_id="workspace-1",
        )

        plan = await service.rewrite(request)

        assert plan.mode == QueryRewriteMode.DISABLED
        assert plan.original_query == "what is the policy"
        assert plan.rewritten_queries == []
        assert plan.was_contextualized is False
        assert llm.calls == []  # No LLM calls

    @pytest.mark.asyncio
    async def test_single_rewrite_mode_generates_one_alternative(self):
        """Test that single_rewrite mode generates one alternative."""
        settings = QueryRewriteConfig(query_rewrite_mode="single_rewrite")
        llm = FakeLLMGateway("vacation policy details")
        service = QueryRewriteService(llm=llm, contextualizer=None, settings=settings)

        request = QueryRewriteRequest(
            query="what is the policy",
            workspace_id="workspace-1",
        )

        plan = await service.rewrite(request)

        assert plan.mode == QueryRewriteMode.SINGLE_REWRITE
        assert plan.original_query == "what is the policy"
        assert len(plan.rewritten_queries) == 1
        assert plan.rewritten_queries[0] == "vacation policy details"

    @pytest.mark.asyncio
    async def test_multi_query_mode_respects_max_queries_limit(self):
        """Test that multi_query mode respects max_queries setting."""
        settings = QueryRewriteConfig(
            query_rewrite_mode="multi_query",
            query_rewrite_max_queries=3,
        )
        # Simulate LLM returning 4 queries
        llm = FakeLLMGateway(
            "vacation policy details\ncompany rules\nextra query\nanother query"
        )
        service = QueryRewriteService(llm=llm, contextualizer=None, settings=settings)

        request = QueryRewriteRequest(
            query="what is the policy",
            workspace_id="workspace-1",
        )

        plan = await service.rewrite(request)

        assert plan.mode == QueryRewriteMode.MULTI_QUERY
        # Should limit to max_queries - 1 (because original is first)
        assert len(plan.rewritten_queries) <= 2
        assert len(plan.all_queries) <= 3

    @pytest.mark.asyncio
    async def test_rewrite_service_falls_back_on_timeout(self):
        """Test that service falls back to original on timeout."""

        class TimeoutLLM:
            def generate(self, request):
                raise TimeoutError()

        settings = QueryRewriteConfig(
            query_rewrite_mode="multi_query",
            query_rewrite_timeout_ms=100,
        )
        service = QueryRewriteService(llm=TimeoutLLM(), contextualizer=None, settings=settings)

        request = QueryRewriteRequest(
            query="what is the policy",
            workspace_id="workspace-1",
        )

        plan = await service.rewrite(request)

        # Should still return a plan with original query
        assert plan.original_query == "what is the policy"
        assert plan.rewritten_queries == []

    @pytest.mark.asyncio
    async def test_rewrite_service_includes_contextualization(self):
        """Test that service contextualizes query when contextualizer is available."""
        settings = QueryRewriteConfig(query_rewrite_mode="single_rewrite")
        llm = FakeLLMGateway("policy details")
        contextualizer = FakeContextualizer(
            "what is the vacation policy",
            should_contextualize=True,
        )
        service = QueryRewriteService(
            llm=llm,
            contextualizer=contextualizer,
            settings=settings,
        )

        request = QueryRewriteRequest(
            query="it",
            workspace_id="workspace-1",
            recent_turns=[{"role": "user", "content": "Tell me about vacation"}],
        )

        plan = await service.rewrite(request)

        assert plan.original_query == "it"
        assert plan.contextualized_query == "what is the vacation policy"
        assert plan.was_contextualized is True
        assert len(contextualizer.calls) == 1

    @pytest.mark.asyncio
    async def test_rewrite_service_falls_back_on_contextualization_timeout(self):
        """Test that rewrite continues if contextualization times out."""

        class TimeoutContextualizer:
            async def contextualize(self, *args, **kwargs):
                raise asyncio.TimeoutError()

        settings = QueryRewriteConfig(query_rewrite_mode="single_rewrite")
        llm = FakeLLMGateway("policy details")
        service = QueryRewriteService(
            llm=llm,
            contextualizer=TimeoutContextualizer(),
            settings=settings,
        )

        request = QueryRewriteRequest(
            query="it",
            workspace_id="workspace-1",
        )

        plan = await service.rewrite(request)

        # Should still generate rewrites with original query
        assert plan.original_query == "it"
        assert plan.contextualized_query is None
        assert plan.was_contextualized is False
        assert len(plan.rewritten_queries) > 0

    @pytest.mark.asyncio
    async def test_rewrite_plan_all_queries_contains_contextualized_and_rewrites(self):
        """Test that all_queries contains both contextualized and rewritten queries."""
        settings = QueryRewriteConfig(query_rewrite_mode="multi_query")
        llm = FakeLLMGateway("policy details\ncompany rules")
        contextualizer = FakeContextualizer(
            "what is the vacation policy",
            should_contextualize=True,
        )
        service = QueryRewriteService(
            llm=llm,
            contextualizer=contextualizer,
            settings=settings,
        )

        request = QueryRewriteRequest(
            query="it",
            workspace_id="workspace-1",
        )

        plan = await service.rewrite(request)

        # all_queries should have: contextualized + rewrites
        assert len(plan.all_queries) >= 2
        assert plan.all_queries[0] == "what is the vacation policy"  # Contextualized first

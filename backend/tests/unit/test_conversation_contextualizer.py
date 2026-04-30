import asyncio
from unittest.mock import Mock

import pytest

from app.core.config.advanced_memory_config import AdvancedMemoryConfig
from app.domain.llm.base import GenerationRequest, GenerationResponse
from app.domain.memory_context.contextualizer import ConversationContextualizer
from app.domain.memory_context.models import ContextualizedTurn
from app.domain.memory_context.packaging_service import MemoryPackagingService


@pytest.fixture
def mock_llm():
    """Create a mock LLM gateway."""
    llm = Mock()
    llm.generate = Mock(
        return_value=GenerationResponse(
            text="What is the company policy on remote work?",
            model="test-model",
            provider="test",
        )
    )
    return llm


@pytest.fixture
def advanced_config():
    """Create advanced memory config."""
    return AdvancedMemoryConfig(
        memory_contextualization_enabled=True,
        memory_retrieval_recent_message_limit=4,
        memory_generation_recent_message_limit=6,
        memory_summary_max_chars=2000,
        memory_contextualization_timeout_ms=2500,
    )


@pytest.fixture
def contextualizer(mock_llm, advanced_config):
    """Create a contextualizer with mocked LLM."""
    return ConversationContextualizer(mock_llm, advanced_config)


@pytest.mark.asyncio
async def test_contextualize_returns_original_when_disabled(mock_llm):
    """Test that original message is returned when contextualization is disabled."""
    config = AdvancedMemoryConfig(memory_contextualization_enabled=False)
    contextualizer = ConversationContextualizer(mock_llm, config)

    result = await contextualizer.contextualize(
        user_message="remote work policy",
        recent_turns=[],
        summary=None,
        workspace_id="ws-123",
    )

    assert result.original_query == "remote work policy"
    assert result.contextualized_query == "remote work policy"
    assert result.was_contextualized is False
    assert result.used_summary is False
    assert result.used_recent_turns == 0
    assert not mock_llm.generate.called


@pytest.mark.asyncio
async def test_contextualize_returns_contextualized_turn_on_success(contextualizer, mock_llm):
    """Test successful contextualization with recent turns."""
    recent_turns = [
        {"role": "user", "content": "What is the company policy?"},
        {"role": "assistant", "content": "I'll help you with that."},
    ]

    result = await contextualizer.contextualize(
        user_message="What about remote work?",
        recent_turns=recent_turns,
        summary="Previous discussions about company policies",
        workspace_id="ws-123",
    )

    assert result.original_query == "What about remote work?"
    assert result.contextualized_query == "What is the company policy on remote work?"
    assert result.was_contextualized is True
    assert result.used_summary is True
    assert result.used_recent_turns == 2
    assert result.metadata["workspace_id"] == "ws-123"
    assert result.metadata["recent_turns_count"] == 2
    assert mock_llm.generate.called


@pytest.mark.asyncio
async def test_contextualize_falls_back_on_timeout(mock_llm, advanced_config):
    """Test fallback to original message on LLM timeout."""
    # Create a mock that will timeout
    async def slow_generate(request):
        await asyncio.sleep(2)
        return GenerationResponse(text="slow", model="test", provider="test")

    # Mock the generate method to be async-compatible by using side_effect
    mock_llm.generate = Mock(side_effect=slow_generate)

    contextualizer = ConversationContextualizer(mock_llm, advanced_config)

    result = await contextualizer.contextualize(
        user_message="test message",
        recent_turns=[],
        summary=None,
        workspace_id="ws-123",
    )

    # Should have original message on timeout
    assert result.original_query == "test message"
    assert result.contextualized_query == "test message"
    assert result.was_contextualized is False
    assert result.metadata.get("timeout") is True


def test_packaging_service_limits_retrieval_messages():
    """Test that packaging service respects RETRIEVAL_RECENT_MESSAGE_LIMIT."""
    config = AdvancedMemoryConfig(memory_retrieval_recent_message_limit=2)
    service = MemoryPackagingService(config)

    messages = [
        {"role": "user", "content": f"message {i}"}
        for i in range(5)
    ]

    package = service.build_for_retrieval(
        conversation_id="conv-123",
        recent_messages=messages,
        summary=None,
    )

    assert package.message_count == 2
    assert len(package.recent_messages) == 2
    # Should get last 2 messages
    assert package.recent_messages[0]["content"] == "message 3"
    assert package.recent_messages[1]["content"] == "message 4"


def test_packaging_service_limits_generation_messages():
    """Test that packaging service respects GENERATION_RECENT_MESSAGE_LIMIT."""
    config = AdvancedMemoryConfig(memory_generation_recent_message_limit=3)
    service = MemoryPackagingService(config)

    messages = [
        {"role": "user", "content": f"message {i}"}
        for i in range(5)
    ]

    package = service.build_for_generation(
        conversation_id="conv-123",
        recent_messages=messages,
        summary=None,
    )

    assert package.message_count == 3
    assert len(package.recent_messages) == 3
    # Should get last 3 messages
    assert package.recent_messages[0]["content"] == "message 2"
    assert package.recent_messages[1]["content"] == "message 3"
    assert package.recent_messages[2]["content"] == "message 4"


def test_packaging_service_truncates_summary_to_max_chars():
    """Test that packaging service truncates summary to max chars."""
    config = AdvancedMemoryConfig(memory_summary_max_chars=50)
    service = MemoryPackagingService(config)

    long_summary = "x" * 200

    package = service.build_for_retrieval(
        conversation_id="conv-123",
        recent_messages=[],
        summary=long_summary,
    )

    assert package.summary_snippet is not None
    assert len(package.summary_snippet) <= 50


@pytest.mark.asyncio
async def test_contextualized_turn_is_workspace_scoped():
    """Test that contextualized turn includes workspace_id for scoping."""
    config = AdvancedMemoryConfig(memory_contextualization_enabled=False)
    contextualizer = ConversationContextualizer(Mock(), config)

    # Need to run async function
    result = await contextualizer.contextualize(
        user_message="test",
        recent_turns=[],
        summary=None,
        workspace_id="ws-456",
    )

    assert result.metadata["workspace_id"] == "ws-456"


def test_advanced_memory_package_combines_retrieval_and_generation():
    """Test that advanced package includes both retrieval and generation."""
    config = AdvancedMemoryConfig(
        memory_retrieval_recent_message_limit=2,
        memory_generation_recent_message_limit=4,
    )
    service = MemoryPackagingService(config)

    messages = [
        {"role": "user", "content": f"message {i}"}
        for i in range(6)
    ]

    package = service.build_advanced(
        conversation_id="conv-123",
        recent_messages=messages,
        summary="Test summary",
    )

    assert package.retrieval is not None
    assert package.generation is not None
    assert package.retrieval.message_count == 2
    assert package.generation.message_count == 4
    assert package.contextualized_turn is None


def test_packaging_service_handles_empty_messages():
    """Test that packaging service handles empty message list."""
    config = AdvancedMemoryConfig()
    service = MemoryPackagingService(config)

    package = service.build_for_retrieval(
        conversation_id="conv-123",
        recent_messages=[],
        summary=None,
    )

    assert package.message_count == 0
    assert len(package.recent_messages) == 0
    assert package.summary_snippet is None

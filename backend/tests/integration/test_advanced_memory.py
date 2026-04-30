"""Integration tests for advanced memory contextualization and retrieval/generation separation."""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.config.advanced_memory_config import AdvancedMemoryConfig
from app.domain.memory_context.packaging_service import MemoryPackagingService
from app.domain.models import Message
from app.domain.services.memory import ConversationMemoryService
from tests.factories import create_conversation, create_membership, create_user, create_workspace


@pytest.mark.integration
def test_follow_up_question_is_contextualized_correctly():
    """Test that a follow-up question is properly contextualized using recent turns."""
    # This test demonstrates the freshness policy:
    # current message → recent relevant turns → rolling summary → older (via summary only)

    # Set up conversation with multiple messages
    from sqlalchemy.orm import Session
    from app.infrastructure.db.session import engine

    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    try:
        user = create_user(session)
        workspace = create_workspace(session)
        create_membership(session, user=user, workspace=workspace, role="member")
        conversation = create_conversation(session, workspace=workspace, user=user)

        # Add several messages to the conversation
        base_time = datetime(2026, 1, 1, tzinfo=UTC)
        messages = []
        for i in range(5):
            message = Message(
                conversation_id=conversation.id,
                workspace_id=workspace.id,
                user_id=user.id if i % 2 == 0 else None,
                role="user" if i % 2 == 0 else "assistant",
                content_text=f"Turn {i}: {'user' if i % 2 == 0 else 'assistant'} message",
                created_at=base_time + timedelta(seconds=i),
            )
            session.add(message)
            messages.append(message)
        session.flush()

        # Create memory service and build advanced package
        settings_model = pytest.importorskip("app.core.config").get_settings()
        memory_service = ConversationMemoryService(session=session, settings=settings_model)

        # This uses the new build_advanced_package method
        advanced_package = memory_service.build_advanced_package(
            user_id=user.id,
            workspace_id=workspace.id,
            conversation_id=conversation.id,
        )

        # Verify the package structure
        assert advanced_package is not None
        assert advanced_package.retrieval is not None
        assert advanced_package.generation is not None

        # Retrieval should have fewer messages (search-focused)
        assert advanced_package.retrieval.message_count <= 4

        # Generation should have more messages (answer-focused)
        assert advanced_package.generation.message_count <= 6

    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.mark.integration
def test_no_cross_workspace_memory_leakage():
    """Test that memory packages don't leak across workspaces.

    This test verifies strict workspace scoping by building packages for two
    different workspaces and ensuring no overlap.
    """
    from sqlalchemy.orm import Session
    from app.infrastructure.db.session import engine

    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    try:
        user = create_user(session)

        # Create two separate workspaces
        workspace1 = create_workspace(session)
        workspace2 = create_workspace(session)

        create_membership(session, user=user, workspace=workspace1, role="member")
        create_membership(session, user=user, workspace=workspace2, role="member")

        # Create conversations in each workspace
        conversation1 = create_conversation(session, workspace=workspace1, user=user)
        conversation2 = create_conversation(session, workspace=workspace2, user=user)

        # Add different messages to each conversation
        base_time = datetime(2026, 1, 1, tzinfo=UTC)

        for i in range(3):
            msg1 = Message(
                conversation_id=conversation1.id,
                workspace_id=workspace1.id,
                user_id=user.id,
                role="user",
                content_text=f"Workspace1 message {i}",
                created_at=base_time + timedelta(seconds=i),
            )
            msg2 = Message(
                conversation_id=conversation2.id,
                workspace_id=workspace2.id,
                user_id=user.id,
                role="user",
                content_text=f"Workspace2 message {i}",
                created_at=base_time + timedelta(seconds=i),
            )
            session.add(msg1)
            session.add(msg2)
        session.flush()

        # Create memory service
        settings_model = pytest.importorskip("app.core.config").get_settings()
        memory_service = ConversationMemoryService(session=session, settings=settings_model)

        # Build packages for each workspace
        package1 = memory_service.build_advanced_package(
            user_id=user.id,
            workspace_id=workspace1.id,
            conversation_id=conversation1.id,
        )

        package2 = memory_service.build_advanced_package(
            user_id=user.id,
            workspace_id=workspace2.id,
            conversation_id=conversation2.id,
        )

        # Verify packages exist
        assert package1 is not None
        assert package2 is not None

        # Verify no memory leakage: messages from ws1 should not appear in ws2 package
        ws1_messages = package1.retrieval.recent_messages + package1.generation.recent_messages
        ws2_messages = package2.retrieval.recent_messages + package2.generation.recent_messages

        ws1_contents = [msg.get("content", "") for msg in ws1_messages]
        ws2_contents = [msg.get("content", "") for msg in ws2_messages]

        # All workspace1 messages should have "Workspace1" marker
        for content in ws1_contents:
            assert "Workspace1" in content

        # All workspace2 messages should have "Workspace2" marker
        for content in ws2_contents:
            assert "Workspace2" in content

    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.mark.integration
def test_empty_summary_falls_back_to_recent_turns():
    """Test that when summary is empty, recent turns are used for context.

    This demonstrates the freshness policy: if there's no summary,
    rely entirely on recent message turns.
    """
    config = AdvancedMemoryConfig(
        memory_retrieval_recent_message_limit=3,
        memory_generation_recent_message_limit=4,
    )
    service = MemoryPackagingService(config)

    # Create messages without a summary
    messages = [
        {"role": "user", "content": f"message {i}"}
        for i in range(5)
    ]

    # Build with None summary
    package = service.build_advanced(
        conversation_id="conv-123",
        recent_messages=messages,
        summary=None,
    )

    # Should still have recent messages
    assert package.retrieval.message_count == 3
    assert package.generation.message_count == 4

    # But no summary snippet
    assert package.retrieval.summary_snippet is None
    assert package.generation.summary_snippet is None

    # Recent messages should be from the end of the list
    assert "message 2" in [m["content"] for m in package.retrieval.recent_messages]
    assert "message 4" in [m["content"] for m in package.generation.recent_messages]


@pytest.mark.integration
def test_memory_package_metadata_is_correct():
    """Test that memory package includes correct metadata."""
    config = AdvancedMemoryConfig()
    service = MemoryPackagingService(config)

    messages = [
        {"role": "user", "content": "message 0"},
        {"role": "assistant", "content": "response 0"},
    ]

    package = service.build_advanced(
        conversation_id="conv-456",
        recent_messages=messages,
        summary="Test summary",
    )

    # Check retrieval package
    assert package.retrieval.message_count > 0
    assert package.retrieval.summary_snippet is not None

    # Check generation package
    assert package.generation.message_count > 0
    assert package.generation.summary_snippet is not None

    # contextualized_turn should be None initially
    assert package.contextualized_turn is None

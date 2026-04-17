from datetime import UTC, datetime, timedelta

import pytest

from app.core.config import ChatMemoryConfig, get_settings
from app.domain.errors import ConversationAccessDenied
from app.domain.models import ConversationSummary, Message
from app.domain.services.memory import ConversationMemoryService
from tests.factories import create_conversation, create_membership, create_user, create_workspace


def test_memory_service_selects_recent_window_without_dumping_full_history(db_session) -> None:
    user, workspace, conversation = setup_conversation(db_session)
    messages = add_messages(db_session, conversation=conversation, user=user, count=6)
    service = memory_service(db_session, recent_limit=3, refresh_every=2)

    package = service.build_memory_package(
        user_id=user.id,
        workspace_id=workspace.id,
        conversation_id=conversation.id,
    )

    assert [message.content for message in package.prompt_memory.recent_messages] == [
        messages[-3].content_text,
        messages[-2].content_text,
        messages[-1].content_text,
    ]
    assert messages[0].content_text not in [message.content for message in package.prompt_memory.recent_messages]


def test_memory_service_persists_summary_for_older_messages(db_session) -> None:
    user, workspace, conversation = setup_conversation(db_session)
    messages = add_messages(db_session, conversation=conversation, user=user, count=6)
    service = memory_service(db_session, recent_limit=2, refresh_every=2)

    package = service.build_memory_package(
        user_id=user.id,
        workspace_id=workspace.id,
        conversation_id=conversation.id,
    )

    summary = db_session.query(ConversationSummary).filter_by(conversation_id=conversation.id).one()
    assert package.summary.id == summary.id
    assert package.prompt_memory.summary == summary.summary_text
    assert summary.summary_version == 1
    assert summary.last_message_id == messages[-3].id
    assert "Earlier conversation:" in summary.summary_text
    assert messages[0].content_text in summary.summary_text
    assert messages[-1].content_text not in summary.summary_text


def test_memory_service_rolls_summary_forward_after_threshold(db_session) -> None:
    user, workspace, conversation = setup_conversation(db_session)
    first_messages = add_messages(db_session, conversation=conversation, user=user, count=5, start_index=0)
    service = memory_service(db_session, recent_limit=2, refresh_every=2)
    first_package = service.build_memory_package(
        user_id=user.id,
        workspace_id=workspace.id,
        conversation_id=conversation.id,
    )

    add_messages(db_session, conversation=conversation, user=user, count=4, start_index=5)
    second_package = service.build_memory_package(
        user_id=user.id,
        workspace_id=workspace.id,
        conversation_id=conversation.id,
    )

    assert first_package.summary.id == second_package.summary.id
    assert second_package.summary.summary_version == 2
    assert first_messages[0].content_text in second_package.summary.summary_text
    assert "message 5" in second_package.summary.summary_text


def test_memory_service_excludes_current_user_message_from_recent_window(db_session) -> None:
    user, workspace, conversation = setup_conversation(db_session)
    messages = add_messages(db_session, conversation=conversation, user=user, count=4)
    service = memory_service(db_session, recent_limit=4, refresh_every=2)

    package = service.build_memory_package(
        user_id=user.id,
        workspace_id=workspace.id,
        conversation_id=conversation.id,
        exclude_message_ids={messages[-1].id},
    )

    assert messages[-1].content_text not in [message.content for message in package.prompt_memory.recent_messages]
    assert [message.content for message in package.prompt_memory.recent_messages] == [
        messages[0].content_text,
        messages[1].content_text,
        messages[2].content_text,
    ]


def test_memory_service_keeps_memory_scoped_to_conversation_and_workspace(db_session) -> None:
    owner, workspace, conversation = setup_conversation(db_session)
    other_user = create_user(db_session, email_prefix="other")
    create_membership(db_session, user=other_user, workspace=workspace, role="member")
    service = memory_service(db_session, recent_limit=3, refresh_every=2)

    with pytest.raises(ConversationAccessDenied):
        service.build_memory_package(
            user_id=other_user.id,
            workspace_id=workspace.id,
            conversation_id=conversation.id,
        )


def test_memory_service_can_disable_summary_generation(db_session) -> None:
    user, workspace, conversation = setup_conversation(db_session)
    add_messages(db_session, conversation=conversation, user=user, count=6)
    service = memory_service(db_session, recent_limit=2, refresh_every=2, summary_enabled=False)

    package = service.build_memory_package(
        user_id=user.id,
        workspace_id=workspace.id,
        conversation_id=conversation.id,
    )

    assert package.summary is None
    assert package.prompt_memory.summary is None
    assert db_session.query(ConversationSummary).filter_by(conversation_id=conversation.id).count() == 0
    assert len(package.prompt_memory.recent_messages) == 2


def setup_conversation(db_session):
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=user, workspace=workspace, role="member")
    conversation = create_conversation(db_session, workspace=workspace, user=user)
    return user, workspace, conversation


def add_messages(db_session, *, conversation, user, count: int, start_index: int = 0) -> list[Message]:
    base_time = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=start_index)
    messages = []
    for offset in range(count):
        role = "user" if (start_index + offset) % 2 == 0 else "assistant"
        message = Message(
            conversation_id=conversation.id,
            workspace_id=conversation.workspace_id,
            user_id=user.id if role == "user" else None,
            role=role,
            content_text=f"{role} message {start_index + offset}",
            created_at=base_time + timedelta(seconds=offset),
        )
        db_session.add(message)
        messages.append(message)
    db_session.flush()
    return messages


def memory_service(db_session, *, recent_limit: int, refresh_every: int, summary_enabled: bool = True) -> ConversationMemoryService:
    settings = get_settings().model_copy(
        update={
            "chat_memory": ChatMemoryConfig(
                recent_messages_limit=recent_limit,
                summary_enabled=summary_enabled,
                summary_refresh_every_n_messages=refresh_every,
            )
        },
        deep=True,
    )
    return ConversationMemoryService(session=db_session, settings=settings)

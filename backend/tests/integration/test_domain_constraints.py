import pytest
from sqlalchemy.exc import IntegrityError

from app.domain.models import Message
from tests.factories import (
    create_conversation,
    create_document,
    create_document_version,
    create_user,
    create_workspace,
)


def test_conversation_requires_existing_workspace(db_session) -> None:
    user = create_user(db_session)
    conversation = create_conversation(db_session, workspace=create_workspace(db_session), user=user)
    conversation.workspace_id = "missing-workspace"

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_message_workspace_must_match_conversation_workspace(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session, slug_prefix="workspace-a")
    other_workspace = create_workspace(db_session, slug_prefix="workspace-b")
    conversation = create_conversation(db_session, workspace=workspace, user=user)

    db_session.add(
        Message(
            conversation_id=conversation.id,
            workspace_id=other_workspace.id,
            user_id=user.id,
            role="user",
            content_text="Question",
        )
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_document_version_requires_existing_document(db_session) -> None:
    user = create_user(db_session)
    document = create_document(db_session, workspace=create_workspace(db_session), created_by=user)
    version = create_document_version(db_session, document=document, created_by=user, version_number=1)
    version.document_id = "missing-document"

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_only_one_active_version_per_document_is_enforced(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    document = create_document(db_session, workspace=workspace, created_by=user)
    create_document_version(db_session, document=document, created_by=user, version_number=1, is_active=True)

    with pytest.raises(IntegrityError):
        create_document_version(db_session, document=document, created_by=user, version_number=2, is_active=True)

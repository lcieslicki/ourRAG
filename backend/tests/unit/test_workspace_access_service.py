import pytest

from app.domain.errors import ConversationAccessDenied, DocumentAccessDenied, WorkspaceAccessDenied
from app.domain.services import WorkspaceAccessService
from tests.factories import (
    create_conversation,
    create_document,
    create_membership,
    create_user,
    create_workspace,
)


def test_workspace_member_is_allowed(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    membership = create_membership(db_session, user=user, workspace=workspace, role="admin")

    resolved = WorkspaceAccessService(db_session).ensure_workspace_member(
        user_id=user.id,
        workspace_id=workspace.id,
    )

    assert resolved.id == membership.id


def test_non_member_is_rejected(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)

    with pytest.raises(WorkspaceAccessDenied):
        WorkspaceAccessService(db_session).ensure_workspace_member(
            user_id=user.id,
            workspace_id=workspace.id,
        )


def test_document_in_requested_workspace_is_allowed(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=user, workspace=workspace)
    document = create_document(db_session, workspace=workspace, created_by=user)

    resolved = WorkspaceAccessService(db_session).ensure_document_access(
        user_id=user.id,
        workspace_id=workspace.id,
        document_id=document.id,
    )

    assert resolved.id == document.id


def test_document_from_another_workspace_is_rejected(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session, slug_prefix="workspace-a")
    other_workspace = create_workspace(db_session, slug_prefix="workspace-b")
    create_membership(db_session, user=user, workspace=workspace)
    other_document = create_document(db_session, workspace=other_workspace, created_by=user)

    with pytest.raises(DocumentAccessDenied):
        WorkspaceAccessService(db_session).ensure_document_access(
            user_id=user.id,
            workspace_id=workspace.id,
            document_id=other_document.id,
        )


def test_conversation_in_requested_workspace_is_allowed(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=user, workspace=workspace)
    conversation = create_conversation(db_session, workspace=workspace, user=user)

    resolved = WorkspaceAccessService(db_session).ensure_conversation_access(
        user_id=user.id,
        workspace_id=workspace.id,
        conversation_id=conversation.id,
    )

    assert resolved.id == conversation.id


def test_conversation_for_another_workspace_is_rejected(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session, slug_prefix="workspace-a")
    other_workspace = create_workspace(db_session, slug_prefix="workspace-b")
    create_membership(db_session, user=user, workspace=workspace)
    other_conversation = create_conversation(db_session, workspace=other_workspace, user=user)

    with pytest.raises(ConversationAccessDenied):
        WorkspaceAccessService(db_session).ensure_conversation_access(
            user_id=user.id,
            workspace_id=workspace.id,
            conversation_id=other_conversation.id,
        )

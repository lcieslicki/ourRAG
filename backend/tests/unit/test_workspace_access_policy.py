import pytest

from app.domain.errors import ConversationAccessDenied, DocumentAccessDenied, WorkspaceAccessDenied
from app.domain.models import Conversation, Document, WorkspaceMembership
from app.domain.services import WorkspaceAccessPolicy


def test_policy_accepts_existing_membership() -> None:
    membership = WorkspaceMembership(user_id="user-1", workspace_id="workspace-1", role="member")

    assert WorkspaceAccessPolicy.require_membership(membership) is membership


def test_policy_rejects_missing_membership() -> None:
    with pytest.raises(WorkspaceAccessDenied):
        WorkspaceAccessPolicy.require_membership(None)


def test_policy_accepts_document_in_workspace() -> None:
    document = Document(
        workspace_id="workspace-1",
        title="Policy",
        slug="policy",
        category="HR",
        tags_json=[],
        created_by_user_id="user-1",
    )

    assert WorkspaceAccessPolicy.require_document_workspace(document, "workspace-1") is document


def test_policy_rejects_document_from_another_workspace() -> None:
    document = Document(
        workspace_id="workspace-2",
        title="Policy",
        slug="policy",
        category="HR",
        tags_json=[],
        created_by_user_id="user-1",
    )

    with pytest.raises(DocumentAccessDenied):
        WorkspaceAccessPolicy.require_document_workspace(document, "workspace-1")


def test_policy_accepts_conversation_for_user_and_workspace() -> None:
    conversation = Conversation(workspace_id="workspace-1", user_id="user-1")

    assert (
        WorkspaceAccessPolicy.require_conversation_workspace(
            conversation,
            user_id="user-1",
            workspace_id="workspace-1",
        )
        is conversation
    )


def test_policy_rejects_conversation_for_another_workspace() -> None:
    conversation = Conversation(workspace_id="workspace-2", user_id="user-1")

    with pytest.raises(ConversationAccessDenied):
        WorkspaceAccessPolicy.require_conversation_workspace(
            conversation,
            user_id="user-1",
            workspace_id="workspace-1",
        )

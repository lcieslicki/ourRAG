from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import Conversation, Document, WorkspaceMembership
from app.domain.services.access_policy import WorkspaceAccessPolicy


class WorkspaceAccessService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def ensure_workspace_member(self, user_id: str, workspace_id: str) -> WorkspaceMembership:
        membership = self.session.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.user_id == user_id,
                WorkspaceMembership.workspace_id == workspace_id,
            )
        )

        return WorkspaceAccessPolicy.require_membership(membership)

    def ensure_workspace_role(self, user_id: str, workspace_id: str, allowed_roles: set[str]) -> WorkspaceMembership:
        membership = self.session.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.user_id == user_id,
                WorkspaceMembership.workspace_id == workspace_id,
            )
        )

        return WorkspaceAccessPolicy.require_role(membership, allowed_roles)

    def ensure_document_access(self, user_id: str, workspace_id: str, document_id: str) -> Document:
        self.ensure_workspace_member(user_id=user_id, workspace_id=workspace_id)

        document = self.session.get(Document, document_id)

        return WorkspaceAccessPolicy.require_document_workspace(document, workspace_id)

    def ensure_conversation_access(self, user_id: str, workspace_id: str, conversation_id: str) -> Conversation:
        self.ensure_workspace_member(user_id=user_id, workspace_id=workspace_id)

        conversation = self.session.get(Conversation, conversation_id)

        return WorkspaceAccessPolicy.require_conversation_workspace(
            conversation,
            user_id=user_id,
            workspace_id=workspace_id,
        )

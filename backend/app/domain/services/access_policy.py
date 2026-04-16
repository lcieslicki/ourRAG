from app.domain.errors import ConversationAccessDenied, DocumentAccessDenied, WorkspaceAccessDenied, WorkspaceRoleDenied
from app.domain.models import Conversation, Document, WorkspaceMembership


class WorkspaceAccessPolicy:
    @staticmethod
    def require_membership(membership: WorkspaceMembership | None) -> WorkspaceMembership:
        if membership is None:
            raise WorkspaceAccessDenied("User is not a member of the workspace.")

        return membership

    @staticmethod
    def require_role(membership: WorkspaceMembership | None, allowed_roles: set[str]) -> WorkspaceMembership:
        membership = WorkspaceAccessPolicy.require_membership(membership)

        if membership.role not in allowed_roles:
            raise WorkspaceRoleDenied("User role is not allowed for this workspace action.")

        return membership

    @staticmethod
    def require_document_workspace(document: Document | None, workspace_id: str) -> Document:
        if document is None or document.workspace_id != workspace_id:
            raise DocumentAccessDenied("Document does not belong to the requested workspace.")

        return document

    @staticmethod
    def require_conversation_workspace(
        conversation: Conversation | None,
        *,
        user_id: str,
        workspace_id: str,
    ) -> Conversation:
        if conversation is None or conversation.workspace_id != workspace_id or conversation.user_id != user_id:
            raise ConversationAccessDenied("Conversation does not belong to the requested workspace and user.")

        return conversation

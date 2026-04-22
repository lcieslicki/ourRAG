from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.domain.errors import ConversationAccessDenied
from app.domain.models import Conversation, Message
from app.domain.services.access import WorkspaceAccessService


class ConversationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.access = WorkspaceAccessService(session)

    def list_workspace_conversations(self, *, user_id: str, workspace_id: str) -> list[Conversation]:
        self.access.ensure_workspace_member(user_id=user_id, workspace_id=workspace_id)
        return list(
            self.session.scalars(
                select(Conversation)
                .where(
                    Conversation.workspace_id == workspace_id,
                    Conversation.user_id == user_id,
                )
                .order_by(Conversation.updated_at.desc(), Conversation.created_at.desc())
            )
        )

    def create_conversation(
        self,
        *,
        user_id: str,
        workspace_id: str,
        title: str | None = None,
        selected_scope: dict | None = None,
    ) -> Conversation:
        self.access.ensure_workspace_member(user_id=user_id, workspace_id=workspace_id)
        conversation = Conversation(
            workspace_id=workspace_id,
            user_id=user_id,
            title=title.strip() if title else None,
            selected_scope_json=selected_scope,
            status="active",
        )
        self.session.add(conversation)
        self.session.flush()
        return conversation

    def delete_workspace_conversations(self, *, user_id: str, workspace_id: str) -> int:
        self.access.ensure_workspace_member(user_id=user_id, workspace_id=workspace_id)
        result = self.session.execute(
            delete(Conversation).where(
                Conversation.workspace_id == workspace_id,
                Conversation.user_id == user_id,
            )
        )
        return int(result.rowcount or 0)

    def get_conversation(self, *, user_id: str, conversation_id: str) -> Conversation:
        conversation = self.session.scalar(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages), selectinload(Conversation.summary))
        )
        if conversation is None:
            raise ConversationAccessDenied("Conversation not found.")

        self.access.ensure_conversation_access(
            user_id=user_id,
            workspace_id=conversation.workspace_id,
            conversation_id=conversation.id,
        )
        return conversation

    def append_user_message(
        self,
        *,
        user_id: str,
        workspace_id: str,
        conversation_id: str,
        content: str,
    ) -> Message:
        conversation = self.access.ensure_conversation_access(
            user_id=user_id,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
        )
        message = Message(
            conversation_id=conversation.id,
            workspace_id=conversation.workspace_id,
            user_id=user_id,
            role="user",
            content_text=self._clean_content(content),
        )
        self.session.add(message)
        self.session.flush()
        return message

    def append_assistant_message(
        self,
        *,
        user_id: str,
        workspace_id: str,
        conversation_id: str,
        content: str,
        response_metadata: dict | None = None,
    ) -> Message:
        conversation = self.access.ensure_conversation_access(
            user_id=user_id,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
        )
        message = Message(
            conversation_id=conversation.id,
            workspace_id=conversation.workspace_id,
            user_id=None,
            role="assistant",
            content_text=self._clean_content(content),
            response_metadata_json=response_metadata,
        )
        self.session.add(message)
        self.session.flush()
        return message

    @staticmethod
    def _clean_content(content: str) -> str:
        cleaned = content.strip()
        if not cleaned:
            raise ValueError("Message content cannot be empty.")
        return cleaned

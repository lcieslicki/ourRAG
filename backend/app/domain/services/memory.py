from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.domain.models import Conversation, ConversationSummary, Message
from app.domain.prompting import ConversationMemory, RecentMessage
from app.domain.services.access import WorkspaceAccessService


@dataclass(frozen=True)
class MemoryPackage:
    prompt_memory: ConversationMemory
    summary: ConversationSummary | None
    retrieval_memory: dict | None = None
    generation_memory: dict | None = None


class ConversationMemoryService:
    def __init__(self, *, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.access = WorkspaceAccessService(session)
        # Advanced memory service will be set if advanced memory is configured
        self._packaging_service = None

    def build_memory_package(
        self,
        *,
        user_id: str,
        workspace_id: str,
        conversation_id: str,
        exclude_message_ids: set[str] | None = None,
    ) -> MemoryPackage:
        conversation = self._conversation_for_access(
            user_id=user_id,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
        )
        excluded_ids = exclude_message_ids or set()
        messages = [
            message
            for message in sorted(conversation.messages, key=lambda item: item.created_at)
            if message.id not in excluded_ids and message.role in {"user", "assistant"}
        ]

        summary = self._refresh_summary_if_needed(conversation=conversation, messages=messages)
        recent_messages = tuple(
            RecentMessage(role=message.role, content=message.content_text)
            for message in messages[-self.settings.chat_memory.recent_messages_limit :]
        )

        return MemoryPackage(
            prompt_memory=ConversationMemory(
                summary=summary.summary_text if summary else None,
                recent_messages=recent_messages,
            ),
            summary=summary,
        )

    def _conversation_for_access(self, *, user_id: str, workspace_id: str, conversation_id: str) -> Conversation:
        self.access.ensure_conversation_access(
            user_id=user_id,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
        )
        return self.session.scalar(
            select(Conversation)
            .where(Conversation.id == conversation_id, Conversation.workspace_id == workspace_id)
            .options(selectinload(Conversation.messages), selectinload(Conversation.summary))
            .execution_options(populate_existing=True)
        )

    def _refresh_summary_if_needed(
        self,
        *,
        conversation: Conversation,
        messages: list[Message],
    ) -> ConversationSummary | None:
        if not self.settings.chat_memory.summary_enabled:
            return conversation.summary

        recent_limit = self.settings.chat_memory.recent_messages_limit
        summarizable = messages[:-recent_limit] if len(messages) > recent_limit else []
        if not summarizable:
            return conversation.summary

        unsummarized = self._unsummarized_messages(conversation.summary, summarizable)
        if conversation.summary and len(unsummarized) < self.settings.chat_memory.summary_refresh_every_n_messages:
            return conversation.summary

        summary_text = build_simple_summary(
            existing_summary=conversation.summary.summary_text if conversation.summary else None,
            messages=unsummarized or summarizable,
        )
        last_message = summarizable[-1]

        if conversation.summary is None:
            summary = ConversationSummary(
                conversation_id=conversation.id,
                summary_text=summary_text,
                summary_version=1,
                last_message_id=last_message.id,
            )
            self.session.add(summary)
            conversation.summary = summary
            self.session.flush()
            return summary

        conversation.summary.summary_text = summary_text
        conversation.summary.summary_version += 1
        conversation.summary.last_message_id = last_message.id
        self.session.flush()
        return conversation.summary

    @staticmethod
    def _unsummarized_messages(summary: ConversationSummary | None, summarizable: list[Message]) -> list[Message]:
        if summary is None or summary.last_message_id is None:
            return summarizable

        for index, message in enumerate(summarizable):
            if message.id == summary.last_message_id:
                return summarizable[index + 1 :]

        return summarizable

    def build_advanced_package(
        self,
        *,
        user_id: str,
        workspace_id: str,
        conversation_id: str,
        exclude_message_ids: set[str] | None = None,
    ) -> "AdvancedMemoryPackage":
        """Build an advanced memory package with retrieval and generation separation.

        This method delegates to MemoryPackagingService to create separate memory
        contexts optimized for retrieval (search intent) and generation (answer shaping).

        Args:
            user_id: The user ID (for access control).
            workspace_id: The workspace ID (for scoping).
            conversation_id: The conversation ID.
            exclude_message_ids: Optional set of message IDs to exclude from memory.

        Returns:
            AdvancedMemoryPackage with both retrieval and generation contexts.

        Raises:
            ConversationAccessDenied: If user doesn't have access to the conversation.
        """
        # Import here to avoid circular imports
        from app.domain.memory_context.packaging_service import MemoryPackagingService
        from app.domain.memory_context.models import AdvancedMemoryPackage
        from app.core.config.advanced_memory_config import AdvancedMemoryConfig

        # Build standard memory package first (for access control and basic processing)
        memory_package = self.build_memory_package(
            user_id=user_id,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            exclude_message_ids=exclude_message_ids,
        )

        # Get configuration (with defaults if not in settings)
        advanced_config = AdvancedMemoryConfig()

        # Get the conversation and recent messages
        conversation = self._conversation_for_access(
            user_id=user_id,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
        )
        excluded_ids = exclude_message_ids or set()
        recent_messages = [
            message
            for message in sorted(conversation.messages, key=lambda item: item.created_at)
            if message.id not in excluded_ids and message.role in {"user", "assistant"}
        ]

        # Build advanced package
        packaging_service = MemoryPackagingService(settings=advanced_config)
        summary_text = memory_package.summary.summary_text if memory_package.summary else None
        return packaging_service.build_advanced(
            conversation_id=conversation_id,
            recent_messages=recent_messages,
            summary=summary_text,
        )


def build_simple_summary(*, existing_summary: str | None, messages: list[Message], max_chars: int = 1600) -> str:
    parts: list[str] = []
    if existing_summary:
        parts.append(existing_summary.strip())

    if messages:
        compact_lines = []
        for message in messages:
            content = " ".join(message.content_text.split())
            if len(content) > 180:
                content = f"{content[:177]}..."
            compact_lines.append(f"{message.role}: {content}")
        parts.append("Earlier conversation:\n" + "\n".join(compact_lines))

    summary = "\n\n".join(part for part in parts if part).strip()
    if len(summary) <= max_chars:
        return summary

    return summary[-max_chars:].lstrip()

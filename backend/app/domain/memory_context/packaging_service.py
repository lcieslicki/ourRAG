from app.core.config.advanced_memory_config import AdvancedMemoryConfig
from .models import (
    AdvancedMemoryPackage,
    GenerationMemoryPackage,
    RetrievalMemoryPackage,
)


class MemoryPackagingService:
    """Service for building memory packages optimized for different use cases.

    This service separates conversation memory into:
    - Retrieval memory: optimized for search/retrieval intent detection
    - Generation memory: optimized for answer generation and shaping

    The separation allows different limits on recent messages and summary inclusion
    based on the use case, following the freshness policy:
    current message → recent relevant turns → rolling summary → older (via summary only)
    """

    def __init__(self, settings: AdvancedMemoryConfig) -> None:
        self.settings = settings

    def build_for_retrieval(
        self,
        conversation_id: str,
        recent_messages: list,
        summary: str | None,
    ) -> RetrievalMemoryPackage:
        """Build a memory package optimized for retrieval/search context.

        Args:
            conversation_id: The conversation ID (for scoping).
            recent_messages: List of recent messages (should be already sorted chronologically).
            summary: Optional conversation summary.

        Returns:
            RetrievalMemoryPackage with selected recent messages and summary.
        """
        # Select last N messages for retrieval
        limit = self.settings.memory_retrieval_recent_message_limit
        selected_messages = recent_messages[-limit:] if recent_messages else []

        # Convert messages to dicts if they're not already
        message_dicts = [
            self._message_to_dict(msg) for msg in selected_messages
        ]

        # Truncate summary to max chars
        summary_snippet = None
        if summary:
            truncated = summary[:self.settings.memory_summary_max_chars]
            summary_snippet = truncated.strip() if truncated.strip() else None

        return RetrievalMemoryPackage(
            recent_messages=message_dicts,
            summary_snippet=summary_snippet,
            message_count=len(message_dicts),
        )

    def build_for_generation(
        self,
        conversation_id: str,
        recent_messages: list,
        summary: str | None,
    ) -> GenerationMemoryPackage:
        """Build a memory package optimized for generation/answer context.

        Args:
            conversation_id: The conversation ID (for scoping).
            recent_messages: List of recent messages (should be already sorted chronologically).
            summary: Optional conversation summary.

        Returns:
            GenerationMemoryPackage with selected recent messages and summary.
        """
        # Select last N messages for generation (typically more than retrieval)
        limit = self.settings.memory_generation_recent_message_limit
        selected_messages = recent_messages[-limit:] if recent_messages else []

        # Convert messages to dicts if they're not already
        message_dicts = [
            self._message_to_dict(msg) for msg in selected_messages
        ]

        # Truncate summary to max chars
        summary_snippet = None
        if summary:
            truncated = summary[:self.settings.memory_summary_max_chars]
            summary_snippet = truncated.strip() if truncated.strip() else None

        return GenerationMemoryPackage(
            recent_messages=message_dicts,
            summary_snippet=summary_snippet,
            message_count=len(message_dicts),
        )

    def build_advanced(
        self,
        conversation_id: str,
        recent_messages: list,
        summary: str | None,
    ) -> AdvancedMemoryPackage:
        """Build a complete advanced memory package with both contexts.

        Args:
            conversation_id: The conversation ID (for scoping).
            recent_messages: List of recent messages (should be already sorted chronologically).
            summary: Optional conversation summary.

        Returns:
            AdvancedMemoryPackage with both retrieval and generation packages.
        """
        retrieval = self.build_for_retrieval(conversation_id, recent_messages, summary)
        generation = self.build_for_generation(conversation_id, recent_messages, summary)

        return AdvancedMemoryPackage(
            retrieval=retrieval,
            generation=generation,
            contextualized_turn=None,
        )

    @staticmethod
    def _message_to_dict(message) -> dict:
        """Convert a message object to a dict.

        Handles both ORM Message objects and dict inputs.

        Args:
            message: A Message ORM object or dict.

        Returns:
            A dict with 'role' and 'content' keys.
        """
        if isinstance(message, dict):
            return {
                "role": message.get("role", "unknown"),
                "content": message.get("content", ""),
            }
        # Assume it's an ORM Message object
        return {
            "role": getattr(message, "role", "unknown"),
            "content": getattr(message, "content_text", ""),
        }

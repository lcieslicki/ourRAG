import asyncio
from typing import Protocol

from app.core.config.advanced_memory_config import AdvancedMemoryConfig
from app.domain.llm.base import GenerationRequest, GenerationResponse
from app.domain.prompting import PromptMessage
from .models import ContextualizedTurn


class LLMGateway(Protocol):
    """Protocol for LLM gateway implementations."""
    def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate text from a request."""
        pass


class ConversationContextualizer:
    """Transforms user messages into standalone questions using conversation context.

    This class contextualizes user messages by:
    1. Checking if contextualization is enabled
    2. Building a prompt with recent turns and summary
    3. Calling the LLM to rewrite the message as a standalone question
    4. Handling timeouts gracefully by returning the original message

    Attributes:
        llm: LLM gateway for generation calls.
        settings: Advanced memory configuration.
    """

    def __init__(self, llm: LLMGateway, settings: AdvancedMemoryConfig) -> None:
        self.llm = llm
        self.settings = settings

    async def contextualize(
        self,
        user_message: str,
        recent_turns: list[dict],
        summary: str | None,
        workspace_id: str,
    ) -> ContextualizedTurn:
        """Contextualize a user message into a standalone question.

        Args:
            user_message: The current user message to contextualize.
            recent_turns: List of recent conversation turns (as dicts with 'role' and 'content').
            summary: Optional summary of older conversation history.
            workspace_id: The workspace ID (for scoping).

        Returns:
            ContextualizedTurn with contextualized_query, was_contextualized flag, and metadata.
        """
        # If contextualization is disabled, return original message
        if not self.settings.memory_contextualization_enabled:
            return ContextualizedTurn(
                original_query=user_message,
                contextualized_query=user_message,
                was_contextualized=False,
                used_summary=False,
                used_recent_turns=0,
                metadata={"workspace_id": workspace_id},
            )

        try:
            contextualized = await asyncio.wait_for(
                self._contextualize_with_llm(user_message, recent_turns, summary),
                timeout=self.settings.memory_contextualization_timeout_ms / 1000.0,
            )
            return ContextualizedTurn(
                original_query=user_message,
                contextualized_query=contextualized,
                was_contextualized=True,
                used_summary=summary is not None and len(summary.strip()) > 0,
                used_recent_turns=len(recent_turns),
                metadata={
                    "workspace_id": workspace_id,
                    "recent_turns_count": len(recent_turns),
                    "summary_provided": summary is not None,
                },
            )
        except asyncio.TimeoutError:
            # Fall back to original message on timeout
            return ContextualizedTurn(
                original_query=user_message,
                contextualized_query=user_message,
                was_contextualized=False,
                used_summary=False,
                used_recent_turns=0,
                metadata={
                    "workspace_id": workspace_id,
                    "timeout": True,
                    "timeout_ms": self.settings.memory_contextualization_timeout_ms,
                },
            )
        except Exception:
            # On any other error, fall back to original message
            return ContextualizedTurn(
                original_query=user_message,
                contextualized_query=user_message,
                was_contextualized=False,
                used_summary=False,
                used_recent_turns=0,
                metadata={
                    "workspace_id": workspace_id,
                    "error": True,
                },
            )

    async def _contextualize_with_llm(
        self,
        user_message: str,
        recent_turns: list[dict],
        summary: str | None,
    ) -> str:
        """Call LLM to contextualize the user message.

        Args:
            user_message: The user message to contextualize.
            recent_turns: Recent conversation turns.
            summary: Optional conversation summary.

        Returns:
            The contextualized message.
        """
        # Build context from recent turns and summary
        context_parts = []

        if summary:
            context_parts.append(f"Previous conversation summary:\n{summary}")

        if recent_turns:
            context_parts.append("Recent conversation:")
            for turn in recent_turns:
                role = turn.get("role", "unknown")
                content = turn.get("content", "")
                context_parts.append(f"{role}: {content}")

        context = "\n".join(context_parts) if context_parts else ""

        # Build the prompt for contextualization
        prompt_text = self._build_contextualization_prompt(user_message, context)

        # Call LLM
        request = GenerationRequest(
            messages=(
                PromptMessage(
                    role="system",
                    content="You are a helpful assistant that rewrites user messages as standalone questions. "
                    "Your task is to take a user message that may reference previous conversation context "
                    "and rewrite it as a clear, standalone question that preserves the intent. "
                    "Return ONLY the rewritten question, nothing else.",
                ),
                PromptMessage(role="user", content=prompt_text),
            ),
        )

        # Run synchronous LLM call in executor to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, self.llm.generate, request)
        return response.text.strip()

    @staticmethod
    def _build_contextualization_prompt(user_message: str, context: str) -> str:
        """Build the contextualization prompt for the LLM.

        Args:
            user_message: The user message to contextualize.
            context: Context from recent turns and summary.

        Returns:
            The complete prompt for the LLM.
        """
        prompt_parts = []

        if context:
            prompt_parts.append(context)
            prompt_parts.append("")

        prompt_parts.append("User message to contextualize:")
        prompt_parts.append(user_message)

        return "\n".join(prompt_parts)

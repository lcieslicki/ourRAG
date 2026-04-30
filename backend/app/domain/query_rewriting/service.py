import asyncio
import logging
from typing import Optional

from app.core.config.query_rewrite_config import QueryRewriteConfig
from app.domain.llm.base import GenerationRequest, LlmGateway
from app.domain.memory_context.contextualizer import ConversationContextualizer
from app.domain.prompting import PromptMessage
from .models import QueryRewriteMode, QueryRewriteRequest, RewritePlan

logger = logging.getLogger(__name__)


class QueryRewriteService:
    """Service for rewriting queries and generating alternative query phrasings.

    This service supports three modes:
    - disabled: Returns original query as-is (safe default).
    - single_rewrite: Generates one alternative phrasing.
    - multi_query: Generates multiple alternative phrasings for broader retrieval.

    Attributes:
        llm: LLM gateway for generation.
        contextualizer: Optional contextualizer for message contextualization.
        settings: Query rewriting configuration.
    """

    def __init__(
        self,
        llm: LlmGateway,
        contextualizer: Optional[ConversationContextualizer],
        settings: QueryRewriteConfig,
    ) -> None:
        self.llm = llm
        self.contextualizer = contextualizer
        self.settings = settings

    async def rewrite(self, request: QueryRewriteRequest) -> RewritePlan:
        """Rewrite a query into alternative phrasings.

        This method:
        1. Returns original query if mode is disabled.
        2. Contextualizes the query if contextualizer is available.
        3. Generates alternative phrasings based on mode.
        4. Returns RewritePlan with all queries.
        5. Falls back to original query on timeout or error.

        Args:
            request: Query rewrite request with query, workspace_id, context.

        Returns:
            RewritePlan with original_query, contextualized_query, rewritten_queries.
        """
        mode = QueryRewriteMode(self.settings.query_rewrite_mode)

        # If disabled, return early with just original query
        if mode == QueryRewriteMode.DISABLED:
            return RewritePlan(
                original_query=request.query,
                mode=mode,
                was_contextualized=False,
            )

        try:
            # Step 1: Contextualize if available
            contextualized_query = request.query
            was_contextualized = False

            if self.contextualizer:
                try:
                    contextualized_turn = await asyncio.wait_for(
                        self.contextualizer.contextualize(
                            user_message=request.query,
                            recent_turns=request.recent_turns,
                            summary=request.summary,
                            workspace_id=request.workspace_id,
                        ),
                        timeout=self.settings.query_rewrite_timeout_ms / 1000.0,
                    )
                    contextualized_query = contextualized_turn.contextualized_query
                    was_contextualized = contextualized_turn.was_contextualized
                except asyncio.TimeoutError:
                    logger.warning(
                        "Query contextualization timed out, falling back to original query"
                    )
                    contextualized_query = request.query
                except Exception as e:
                    logger.warning(
                        f"Query contextualization failed: {e}, falling back to original query"
                    )
                    contextualized_query = request.query

            # Step 2: Generate rewrites based on mode
            rewritten_queries: list[str] = []

            if mode == QueryRewriteMode.SINGLE_REWRITE:
                rewritten_queries = await self._generate_rewrites(
                    query=contextualized_query,
                    num_rewrites=1,
                    request=request,
                )
            elif mode == QueryRewriteMode.MULTI_QUERY:
                rewritten_queries = await self._generate_rewrites(
                    query=contextualized_query,
                    num_rewrites=self.settings.query_rewrite_max_queries,
                    request=request,
                )

            return RewritePlan(
                original_query=request.query,
                contextualized_query=contextualized_query if was_contextualized else None,
                rewritten_queries=rewritten_queries,
                mode=mode,
                was_contextualized=was_contextualized,
            )

        except asyncio.TimeoutError:
            logger.warning(
                "Query rewriting timed out, falling back to original query only"
            )
            return RewritePlan(
                original_query=request.query,
                mode=mode,
                was_contextualized=False,
            )
        except Exception as e:
            logger.error(f"Query rewriting failed: {e}, falling back to original query")
            return RewritePlan(
                original_query=request.query,
                mode=mode,
                was_contextualized=False,
            )

    async def _generate_rewrites(
        self,
        query: str,
        num_rewrites: int,
        request: QueryRewriteRequest,
    ) -> list[str]:
        """Generate alternative query phrasings.

        Args:
            query: The query to rewrite.
            num_rewrites: Number of rewrites to generate.
            request: Original request for context.

        Returns:
            List of alternative query phrasings.
        """
        try:
            prompt = self._build_rewrite_prompt(
                query=query,
                num_rewrites=num_rewrites,
                request=request,
            )

            # Run LLM call with timeout
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.llm.generate(
                        GenerationRequest(
                            messages=(
                                PromptMessage(
                                    role="system",
                                    content="You are an expert at generating alternative search queries. "
                                    "Generate alternative phrasings of the given search query. "
                                    "Each query should preserve the original intent but use different wording, synonyms, or approaches. "
                                    "Return ONLY the queries, one per line, without numbering or additional explanation.",
                                ),
                                PromptMessage(role="user", content=prompt),
                            ),
                        )
                    ),
                ),
                timeout=self.settings.query_rewrite_timeout_ms / 1000.0,
            )

            # Parse response into individual queries
            rewrites = [
                q.strip()
                for q in response.text.strip().split("\n")
                if q.strip() and q.strip() != query
            ]

            # Limit to requested number
            return rewrites[: num_rewrites - 1]  # -1 because original is included

        except asyncio.TimeoutError:
            logger.warning(f"Rewrite generation timed out for query: {query}")
            return []
        except Exception as e:
            logger.error(f"Rewrite generation failed for query: {query}, error: {e}")
            return []

    @staticmethod
    def _build_rewrite_prompt(
        query: str,
        num_rewrites: int,
        request: QueryRewriteRequest,
    ) -> str:
        """Build the prompt for LLM to generate query rewrites.

        Args:
            query: The query to rewrite.
            num_rewrites: Number of alternative phrasings to generate.
            request: Original request for context.

        Returns:
            The prompt string for the LLM.
        """
        prompt_parts = []

        prompt_parts.append(f"Generate {num_rewrites} alternative search queries:")
        prompt_parts.append("")
        prompt_parts.append(f"Original query: {query}")

        # Include context if available
        if request.recent_turns and request.recent_turns:
            prompt_parts.append("")
            prompt_parts.append("Recent conversation context:")
            for turn in request.recent_turns[-2:]:  # Last 2 turns for brevity
                role = turn.get("role", "unknown").capitalize()
                content = turn.get("content", "")[:100]  # Truncate for brevity
                prompt_parts.append(f"  {role}: {content}...")

        if request.summary:
            prompt_parts.append("")
            prompt_parts.append(f"Conversation summary: {request.summary[:200]}...")

        prompt_parts.append("")
        prompt_parts.append("Alternative queries (different wording, synonyms, or approaches):")

        return "\n".join(prompt_parts)

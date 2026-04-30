from enum import Enum

from pydantic import BaseModel, Field


class QueryRewriteMode(str, Enum):
    """Enumeration of query rewrite modes."""
    DISABLED = "disabled"
    SINGLE_REWRITE = "single_rewrite"
    MULTI_QUERY = "multi_query"


class RewritePlan(BaseModel):
    """Plan for query rewriting containing original and rewritten queries.

    Attributes:
        original_query: The original user query.
        contextualized_query: The query after contextualization (if available).
        rewritten_queries: List of alternative phrasings of the original query.
        mode: The query rewrite mode used.
        was_contextualized: Whether the query was contextualized.
    """
    original_query: str
    contextualized_query: str | None = None
    rewritten_queries: list[str] = Field(default_factory=list)
    mode: QueryRewriteMode = QueryRewriteMode.DISABLED
    was_contextualized: bool = False

    @property
    def all_queries(self) -> list[str]:
        """Return all queries (contextualized or original + rewrites), deduplicated.

        Returns list of queries with contextualized_query (if available) first,
        followed by rewritten_queries, with duplicates removed.
        """
        all_q = []

        # Add contextualized query first if available
        if self.contextualized_query:
            all_q.append(self.contextualized_query)
        else:
            all_q.append(self.original_query)

        # Add rewritten queries, excluding duplicates
        seen = {all_q[0]}
        for rewritten in self.rewritten_queries:
            if rewritten not in seen:
                all_q.append(rewritten)
                seen.add(rewritten)

        return all_q


class QueryRewriteRequest(BaseModel):
    """Request for query rewriting and contextualization.

    Attributes:
        query: The user query to rewrite.
        workspace_id: The workspace ID for scope validation.
        recent_turns: List of recent conversation turns.
        summary: Conversation summary (if available).
        active_filters: Active filters to preserve during retrieval.
    """
    query: str
    workspace_id: str
    recent_turns: list[dict] = Field(default_factory=list)
    summary: str | None = None
    active_filters: dict = Field(default_factory=dict)

"""
Guardrails and answer policy (A4).

Backend-authoritative decision: determines response_mode before generation.
Response modes: answer_from_context | refuse_out_of_scope | insufficient_context
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence

from app.domain.services.retrieval import RetrievedChunk

logger = logging.getLogger(__name__)


class ResponseMode(str, Enum):
    ANSWER_FROM_CONTEXT = "answer_from_context"
    REFUSE_OUT_OF_SCOPE = "refuse_out_of_scope"
    INSUFFICIENT_CONTEXT = "insufficient_context"


@dataclass(frozen=True)
class GuardrailDecision:
    response_mode: ResponseMode
    guardrail_reason: str | None = None
    guardrail_signals: dict = field(default_factory=dict)

    @property
    def should_generate(self) -> bool:
        return self.response_mode == ResponseMode.ANSWER_FROM_CONTEXT


# ── Template responses ────────────────────────────────────────────────────────

TEMPLATE_RESPONSES: dict[ResponseMode, str] = {
    ResponseMode.REFUSE_OUT_OF_SCOPE: (
        "Przepraszam, to pytanie wykracza poza zakres dokumentów dostępnych w tym workspace. "
        "Mogę pomóc tylko w tematach objętych załadowaną dokumentacją."
    ),
    ResponseMode.INSUFFICIENT_CONTEXT: (
        "Nie mam wystarczających informacji w udostępnionej dokumentacji, "
        "aby pewnie odpowiedzieć na to pytanie. "
        "Jeśli posiadasz odpowiedni dokument, prześlij go do workspace."
    ),
}

# ── Out-of-scope heuristics ───────────────────────────────────────────────────

# Keywords that strongly suggest off-domain requests
_OUT_OF_SCOPE_KEYWORDS: frozenset[str] = frozenset(
    {
        # Generic off-domain topics
        "bitcoin", "crypto", "ethereum", "blockchain",
        "recipe", "cooking", "restaurant",
        "weather", "forecast",
        "movie", "film", "actor",
        "sport", "football", "soccer", "basketball",
        "stock", "investment", "trading",
        # System prompts / jailbreaks
        "ignore previous", "disregard", "pretend you are",
        "as an ai", "as a language model",
    }
)

# Short conversational turns that are always in scope
_CONVERSATIONAL_TURNS: frozenset[str] = frozenset(
    {
        "hello", "hi", "cześć", "dzień dobry", "dobry wieczór",
        "dziękuję", "dzięki", "thank you", "thanks",
        "do widzenia", "pa", "bye", "goodbye",
        "ok", "okej", "okay", "rozumiem",
    }
)


class GuardrailService:
    """
    Evaluates whether a chat request should proceed to generation.

    Decision order (matching spec):
    1. Is the message conversational? → allow without retrieval check
    2. Is the query in scope? (rule-based) → refuse_out_of_scope
    3. Is the retrieved evidence sufficient? → insufficient_context
    4. Otherwise → answer_from_context
    """

    def __init__(
        self,
        *,
        enabled: bool = True,
        in_scope_required: bool = True,
        min_top_score: float = 0.72,
        min_usable_chunks: int = 2,
        use_template_responses: bool = True,
    ) -> None:
        self.enabled = enabled
        self.in_scope_required = in_scope_required
        self.min_top_score = min_top_score
        self.min_usable_chunks = min_usable_chunks
        self.use_template_responses = use_template_responses

    def evaluate(
        self,
        *,
        query: str,
        retrieved_chunks: Sequence[RetrievedChunk],
        workspace_domain_hints: Sequence[str] | None = None,
    ) -> GuardrailDecision:
        """
        Returns a GuardrailDecision for the given query and retrieval result.
        """
        if not self.enabled:
            return GuardrailDecision(response_mode=ResponseMode.ANSWER_FROM_CONTEXT)

        # Conversational turns bypass all checks
        if self._is_conversational(query):
            return GuardrailDecision(response_mode=ResponseMode.ANSWER_FROM_CONTEXT)

        # Scope check
        if self.in_scope_required and self._is_out_of_scope(query):
            logger.info("guardrail.refuse_out_of_scope query_preview=%s", query[:80])
            return GuardrailDecision(
                response_mode=ResponseMode.REFUSE_OUT_OF_SCOPE,
                guardrail_reason="out_of_scope_query",
                guardrail_signals={"matched_keywords": self._matched_keywords(query)},
            )

        # Retrieval sufficiency gate
        top_score = retrieved_chunks[0].score if retrieved_chunks else 0.0
        usable_chunk_count = sum(
            1 for c in retrieved_chunks if c.score >= self.min_top_score
        )

        signals = {
            "top_score": top_score,
            "usable_chunks": usable_chunk_count,
            "total_chunks": len(retrieved_chunks),
            "min_top_score_threshold": self.min_top_score,
            "min_usable_chunks_threshold": self.min_usable_chunks,
        }

        if top_score < self.min_top_score or usable_chunk_count < self.min_usable_chunks:
            logger.info(
                "guardrail.insufficient_context top_score=%.3f usable=%d",
                top_score,
                usable_chunk_count,
            )
            return GuardrailDecision(
                response_mode=ResponseMode.INSUFFICIENT_CONTEXT,
                guardrail_reason="retrieval_below_threshold",
                guardrail_signals=signals,
            )

        return GuardrailDecision(
            response_mode=ResponseMode.ANSWER_FROM_CONTEXT,
            guardrail_signals=signals,
        )

    def get_template_response(self, mode: ResponseMode) -> str | None:
        if not self.use_template_responses:
            return None
        return TEMPLATE_RESPONSES.get(mode)

    @staticmethod
    def _is_conversational(query: str) -> bool:
        return query.strip().lower() in _CONVERSATIONAL_TURNS

    @staticmethod
    def _is_out_of_scope(query: str) -> bool:
        q_lower = query.lower()
        return any(kw in q_lower for kw in _OUT_OF_SCOPE_KEYWORDS)

    @staticmethod
    def _matched_keywords(query: str) -> list[str]:
        q_lower = query.lower()
        return [kw for kw in _OUT_OF_SCOPE_KEYWORDS if kw in q_lower]

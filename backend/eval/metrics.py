"""
Evaluation metrics for the ourRAG evaluation suite (A5).

Metrics:
- hit@k            : fraction of cases where expected doc appears in top-k retrieved
- mrr              : Mean Reciprocal Rank for the first correct document
- answer_signal_coverage : fraction of expected answer signals found in the response
- citation_presence: fraction of cases where at least one citation was returned
- response_mode_accuracy: fraction of cases with correct response_mode
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass
class CaseResult:
    case_id: str
    question: str
    retrieved_doc_titles: list[str]
    answer_text: str
    response_mode: str
    citation_count: int
    expected_source_documents: list[str]
    expected_answer_signals: list[str]
    expected_response_mode: str
    latency_ms: float | None = None
    # computed
    hit: bool = False
    reciprocal_rank: float = 0.0
    signal_coverage: float = 0.0
    has_citation: bool = False
    mode_correct: bool = False


@dataclass
class EvalReport:
    total_cases: int
    hit_at_k: float
    mrr: float
    answer_signal_coverage: float
    citation_presence: float
    response_mode_accuracy: float
    average_latency_ms: float | None = None
    case_results: list[CaseResult] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def compute_hit_at_k(
    retrieved_titles: list[str],
    expected_titles: list[str],
) -> bool:
    """Returns True if any expected document title appears in retrieved titles."""
    if not expected_titles:
        return True  # no expectation → not penalized
    retrieved_lower = {t.lower() for t in retrieved_titles}
    return any(e.lower() in retrieved_lower for e in expected_titles)


def compute_reciprocal_rank(
    retrieved_titles: list[str],
    expected_titles: list[str],
) -> float:
    """Returns 1/rank of the first correct document, or 0.0 if none found."""
    if not expected_titles:
        return 1.0
    expected_lower = {e.lower() for e in expected_titles}
    for rank, title in enumerate(retrieved_titles, start=1):
        if title.lower() in expected_lower:
            return 1.0 / rank
    return 0.0


def compute_signal_coverage(
    answer_text: str,
    expected_signals: list[str],
) -> float:
    """Fraction of expected answer signals found in answer text (case-insensitive)."""
    if not expected_signals:
        return 1.0
    answer_lower = answer_text.lower()
    hits = sum(1 for signal in expected_signals if signal.lower() in answer_lower)
    return hits / len(expected_signals)


def compute_metrics(results: Sequence[CaseResult]) -> EvalReport:
    if not results:
        return EvalReport(
            total_cases=0,
            hit_at_k=0.0,
            mrr=0.0,
            answer_signal_coverage=0.0,
            citation_presence=0.0,
            response_mode_accuracy=0.0,
        )

    n = len(results)
    latencies = [r.latency_ms for r in results if r.latency_ms is not None]

    return EvalReport(
        total_cases=n,
        hit_at_k=sum(r.hit for r in results) / n,
        mrr=sum(r.reciprocal_rank for r in results) / n,
        answer_signal_coverage=sum(r.signal_coverage for r in results) / n,
        citation_presence=sum(r.has_citation for r in results) / n,
        response_mode_accuracy=sum(r.mode_correct for r in results) / n,
        average_latency_ms=sum(latencies) / len(latencies) if latencies else None,
        case_results=list(results),
    )


def evaluate_case(
    case_result: CaseResult,
) -> CaseResult:
    """Fill computed fields in a CaseResult."""
    case_result.hit = compute_hit_at_k(
        case_result.retrieved_doc_titles,
        case_result.expected_source_documents,
    )
    case_result.reciprocal_rank = compute_reciprocal_rank(
        case_result.retrieved_doc_titles,
        case_result.expected_source_documents,
    )
    case_result.signal_coverage = compute_signal_coverage(
        case_result.answer_text,
        case_result.expected_answer_signals,
    )
    case_result.has_citation = case_result.citation_count > 0
    case_result.mode_correct = (
        case_result.response_mode == case_result.expected_response_mode
    )
    return case_result

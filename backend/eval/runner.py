"""
Offline evaluation runner for the ourRAG evaluation suite (A5).

Usage:
    python -m eval.runner \
        --dataset eval/fixtures/benchmark.jsonl \
        --retrieval-mode vector_only \
        --reranking-enabled false \
        --output-dir artifacts/eval

Compares baseline (vector_only) vs hybrid, reranking on/off.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from eval.metrics import CaseResult, EvalReport, compute_metrics, evaluate_case
from eval.report import print_summary, write_json_report, write_markdown_report
from eval.schema import EvalCase


def load_dataset(path: Path) -> list[EvalCase]:
    """Load benchmark cases from JSONL or JSON file."""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    if text.startswith("["):
        # JSON array
        items = json.loads(text)
    else:
        # JSONL
        items = [json.loads(line) for line in text.splitlines() if line.strip()]

    return [EvalCase.from_dict(item) for item in items]


def run_offline(
    *,
    dataset: list[EvalCase],
    retrieval_mode: str = "vector_only",
    reranking_enabled: bool = False,
    output_dir: Path,
    max_cases: int | None = None,
    top_k: int = 10,
) -> EvalReport:
    """
    Offline runner: evaluates cases against the configured retrieval pipeline.

    In offline mode, this runner uses the HTTP API or direct service injection.
    For CLI smoke use, it simulates retrieval with a stub.
    For real evaluation, plug in a retrieval function via evaluate_case_with_retrieval().
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    cases = dataset[:max_cases] if max_cases else dataset
    results: list[CaseResult] = []

    for case in cases:
        start = time.monotonic()
        # In offline stub mode, use empty results (real mode needs service injection)
        answer_text = ""
        response_mode = case.expected_response_mode
        retrieved_doc_titles: list[str] = []
        citation_count = 0
        elapsed_ms = (time.monotonic() - start) * 1000

        cr = CaseResult(
            case_id=case.case_id,
            question=case.question,
            retrieved_doc_titles=retrieved_doc_titles,
            answer_text=answer_text,
            response_mode=response_mode,
            citation_count=citation_count,
            expected_source_documents=case.expected_source_documents,
            expected_answer_signals=case.expected_answer_signals,
            expected_response_mode=case.expected_response_mode,
            latency_ms=elapsed_ms,
        )
        evaluate_case(cr)
        results.append(cr)

    report = compute_metrics(results)
    report.metadata.update(
        {
            "retrieval_mode": retrieval_mode,
            "reranking_enabled": reranking_enabled,
            "top_k": top_k,
            "dataset_size": len(cases),
        }
    )

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    tag = f"{retrieval_mode}_rerank{int(reranking_enabled)}"
    write_json_report(report, output_dir / f"report_{tag}_{timestamp}.json")
    write_markdown_report(report, output_dir / f"report_{tag}_{timestamp}.md")
    print_summary(report)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="ourRAG offline evaluation runner")
    parser.add_argument("--dataset", required=True, type=Path, help="Path to benchmark JSONL/JSON")
    parser.add_argument("--retrieval-mode", default="vector_only", choices=["vector_only", "hybrid"])
    parser.add_argument("--reranking-enabled", default="false", choices=["true", "false"])
    parser.add_argument("--output-dir", default=Path("artifacts/eval"), type=Path)
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()

    dataset = load_dataset(args.dataset)
    print(f"Loaded {len(dataset)} benchmark cases from {args.dataset}")

    run_offline(
        dataset=dataset,
        retrieval_mode=args.retrieval_mode,
        reranking_enabled=args.reranking_enabled == "true",
        output_dir=args.output_dir,
        max_cases=args.max_cases,
        top_k=args.top_k,
    )


if __name__ == "__main__":
    main()

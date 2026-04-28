"""
Report writer for the evaluation suite (A5).
Produces machine-readable JSON and human-readable Markdown.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from eval.metrics import EvalReport


def write_json_report(report: EvalReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "total_cases": report.total_cases,
            "hit_at_k": round(report.hit_at_k, 4),
            "mrr": round(report.mrr, 4),
            "answer_signal_coverage": round(report.answer_signal_coverage, 4),
            "citation_presence": round(report.citation_presence, 4),
            "response_mode_accuracy": round(report.response_mode_accuracy, 4),
            "average_latency_ms": round(report.average_latency_ms, 1) if report.average_latency_ms else None,
        },
        "metadata": report.metadata,
        "cases": [
            {
                "case_id": r.case_id,
                "question": r.question,
                "response_mode": r.response_mode,
                "expected_response_mode": r.expected_response_mode,
                "hit": r.hit,
                "reciprocal_rank": round(r.reciprocal_rank, 4),
                "signal_coverage": round(r.signal_coverage, 4),
                "has_citation": r.has_citation,
                "mode_correct": r.mode_correct,
                "latency_ms": r.latency_ms,
                "retrieved_doc_titles": r.retrieved_doc_titles,
            }
            for r in report.case_results
        ],
    }
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_markdown_report(report: EvalReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# ourRAG Evaluation Report",
        "",
        f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total cases | {report.total_cases} |",
        f"| hit@k | {report.hit_at_k:.1%} |",
        f"| MRR | {report.mrr:.4f} |",
        f"| Answer signal coverage | {report.answer_signal_coverage:.1%} |",
        f"| Citation presence | {report.citation_presence:.1%} |",
        f"| Response mode accuracy | {report.response_mode_accuracy:.1%} |",
    ]
    if report.average_latency_ms is not None:
        lines.append(f"| Avg latency | {report.average_latency_ms:.0f} ms |")

    lines += [
        "",
        "## Case Results",
        "",
        "| case_id | hit | MRR | signal_cov | citation | mode_ok | latency_ms |",
        "|---------|-----|-----|-----------|----------|---------|------------|",
    ]
    for r in report.case_results:
        lines.append(
            f"| {r.case_id} "
            f"| {'✓' if r.hit else '✗'} "
            f"| {r.reciprocal_rank:.2f} "
            f"| {r.signal_coverage:.0%} "
            f"| {'✓' if r.has_citation else '✗'} "
            f"| {'✓' if r.mode_correct else '✗'} "
            f"| {r.latency_ms:.0f}ms |" if r.latency_ms else
            f"| {r.case_id} "
            f"| {'✓' if r.hit else '✗'} "
            f"| {r.reciprocal_rank:.2f} "
            f"| {r.signal_coverage:.0%} "
            f"| {'✓' if r.has_citation else '✗'} "
            f"| {'✓' if r.mode_correct else '✗'} "
            f"| — |"
        )

    output_path.write_text("\n".join(lines), encoding="utf-8")


def print_summary(report: EvalReport) -> None:
    print(f"\n{'=' * 50}")
    print(f"ourRAG Evaluation Summary  ({report.total_cases} cases)")
    print(f"{'=' * 50}")
    print(f"  hit@k                 : {report.hit_at_k:.1%}")
    print(f"  MRR                   : {report.mrr:.4f}")
    print(f"  answer signal coverage: {report.answer_signal_coverage:.1%}")
    print(f"  citation presence     : {report.citation_presence:.1%}")
    print(f"  response mode accuracy: {report.response_mode_accuracy:.1%}")
    if report.average_latency_ms:
        print(f"  avg latency           : {report.average_latency_ms:.0f} ms")
    print(f"{'=' * 50}\n")

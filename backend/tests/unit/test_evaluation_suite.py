"""Unit tests for the evaluation suite (A5)."""

import json
import tempfile
from pathlib import Path

import pytest

from eval.metrics import (
    CaseResult,
    compute_hit_at_k,
    compute_metrics,
    compute_reciprocal_rank,
    compute_signal_coverage,
    evaluate_case,
)
from eval.report import write_json_report, write_markdown_report
from eval.runner import load_dataset
from eval.schema import EvalCase


# ── Dataset schema ────────────────────────────────────────────────────────────

def test_eval_case_from_dict_parses_all_fields() -> None:
    data = {
        "case_id": "test_001",
        "workspace_fixture": "firma_abc",
        "question": "Ile dni urlopu?",
        "expected_source_documents": ["hr_polityka_urlopowa.md"],
        "expected_answer_signals": ["20 dni", "urlop"],
        "expected_response_mode": "answer_from_context",
        "tags": ["hr", "vacation"],
        "notes": "Standardowe pytanie HR",
    }
    case = EvalCase.from_dict(data)
    assert case.case_id == "test_001"
    assert case.workspace_fixture == "firma_abc"
    assert "20 dni" in case.expected_answer_signals
    assert case.expected_response_mode == "answer_from_context"


def test_eval_case_to_dict_roundtrip() -> None:
    data = {
        "case_id": "rt_001",
        "workspace_fixture": "ws",
        "question": "Q?",
        "expected_source_documents": ["doc.md"],
        "expected_answer_signals": ["signal"],
        "expected_response_mode": "answer_from_context",
    }
    case = EvalCase.from_dict(data)
    assert case.to_dict()["case_id"] == "rt_001"
    assert case.to_dict()["expected_answer_signals"] == ["signal"]


# ── Metric computation ────────────────────────────────────────────────────────

def test_hit_at_k_true_when_doc_in_retrieved() -> None:
    assert compute_hit_at_k(["HR Policy", "IT Guide"], ["HR Policy"]) is True


def test_hit_at_k_false_when_doc_not_in_retrieved() -> None:
    assert compute_hit_at_k(["Finance Report"], ["HR Policy"]) is False


def test_hit_at_k_true_when_no_expectation() -> None:
    assert compute_hit_at_k([], []) is True


def test_reciprocal_rank_correct_first_position() -> None:
    assert compute_reciprocal_rank(["HR Policy", "Finance"], ["HR Policy"]) == pytest.approx(1.0)


def test_reciprocal_rank_correct_second_position() -> None:
    assert compute_reciprocal_rank(["Finance", "HR Policy"], ["HR Policy"]) == pytest.approx(0.5)


def test_reciprocal_rank_zero_when_not_found() -> None:
    assert compute_reciprocal_rank(["Finance", "IT Guide"], ["HR Policy"]) == pytest.approx(0.0)


def test_signal_coverage_all_signals_found() -> None:
    assert compute_signal_coverage("Firma płaci 100% kosztów szkoleń", ["100%", "firma"]) == pytest.approx(1.0)


def test_signal_coverage_partial() -> None:
    coverage = compute_signal_coverage("Firma płaci koszty", ["100%", "firma"])
    assert coverage == pytest.approx(0.5)


def test_signal_coverage_none_found() -> None:
    assert compute_signal_coverage("Unrelated text", ["100%", "firma"]) == pytest.approx(0.0)


def test_signal_coverage_empty_signals() -> None:
    assert compute_signal_coverage("Any answer", []) == pytest.approx(1.0)


# ── evaluate_case fills computed fields ──────────────────────────────────────

def test_evaluate_case_sets_hit_and_mode_correct() -> None:
    cr = CaseResult(
        case_id="c1",
        question="Q?",
        retrieved_doc_titles=["HR Policy"],
        answer_text="Firma płaci 100% kosztów",
        response_mode="answer_from_context",
        citation_count=2,
        expected_source_documents=["HR Policy"],
        expected_answer_signals=["100%"],
        expected_response_mode="answer_from_context",
        latency_ms=120.0,
    )
    evaluate_case(cr)
    assert cr.hit is True
    assert cr.has_citation is True
    assert cr.mode_correct is True
    assert cr.signal_coverage == pytest.approx(1.0)


def test_evaluate_case_sets_false_when_wrong_mode() -> None:
    cr = CaseResult(
        case_id="c2",
        question="Q?",
        retrieved_doc_titles=[],
        answer_text="",
        response_mode="insufficient_context",
        citation_count=0,
        expected_source_documents=["HR Policy"],
        expected_answer_signals=[],
        expected_response_mode="answer_from_context",
    )
    evaluate_case(cr)
    assert cr.mode_correct is False
    assert cr.hit is False


# ── compute_metrics aggregation ───────────────────────────────────────────────

def test_compute_metrics_aggregates_correctly() -> None:
    cr1 = CaseResult("c1", "Q1?", ["Doc A"], "answer with signal X", "answer_from_context", 1, ["Doc A"], ["signal X"], "answer_from_context", latency_ms=100.0)
    cr2 = CaseResult("c2", "Q2?", ["Doc B"], "no signal", "answer_from_context", 0, ["Doc A"], ["signal X"], "answer_from_context", latency_ms=200.0)
    evaluate_case(cr1)
    evaluate_case(cr2)

    report = compute_metrics([cr1, cr2])
    assert report.total_cases == 2
    assert report.hit_at_k == pytest.approx(0.5)  # only cr1 hits
    assert report.citation_presence == pytest.approx(0.5)  # only cr1 has citations
    assert report.average_latency_ms == pytest.approx(150.0)


def test_compute_metrics_empty_input() -> None:
    report = compute_metrics([])
    assert report.total_cases == 0
    assert report.hit_at_k == 0.0


# ── Report writer ─────────────────────────────────────────────────────────────

def test_write_json_report_produces_valid_json() -> None:
    cr = CaseResult("c1", "Q?", ["Doc A"], "answer", "answer_from_context", 1, ["Doc A"], ["answer"], "answer_from_context", latency_ms=50.0)
    evaluate_case(cr)
    report = compute_metrics([cr])

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "report.json"
        write_json_report(report, out)
        data = json.loads(out.read_text())
        assert data["summary"]["total_cases"] == 1
        assert "hit_at_k" in data["summary"]
        assert len(data["cases"]) == 1


def test_write_markdown_report_produces_md_content() -> None:
    cr = CaseResult("c1", "Q?", [], "answer", "answer_from_context", 0, [], [], "answer_from_context")
    evaluate_case(cr)
    report = compute_metrics([cr])

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "report.md"
        write_markdown_report(report, out)
        content = out.read_text()
        assert "ourRAG Evaluation Report" in content
        assert "hit@k" in content


# ── Dataset loading ───────────────────────────────────────────────────────────

def test_load_dataset_from_jsonl() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        jsonl = Path(tmp) / "bench.jsonl"
        jsonl.write_text(
            json.dumps({
                "case_id": "t1",
                "workspace_fixture": "fw",
                "question": "Q?",
                "expected_source_documents": [],
                "expected_answer_signals": [],
                "expected_response_mode": "answer_from_context",
            }) + "\n"
        )
        cases = load_dataset(jsonl)
        assert len(cases) == 1
        assert cases[0].case_id == "t1"


def test_load_dataset_from_json_array() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        jf = Path(tmp) / "bench.json"
        jf.write_text(json.dumps([
            {
                "case_id": "t2",
                "workspace_fixture": "fw",
                "question": "Q2?",
                "expected_source_documents": ["doc.md"],
                "expected_answer_signals": [],
                "expected_response_mode": "answer_from_context",
            }
        ]))
        cases = load_dataset(jf)
        assert len(cases) == 1
        assert cases[0].case_id == "t2"

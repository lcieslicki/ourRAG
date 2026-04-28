"""
Benchmark dataset schema for the evaluation suite (A5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvalCase:
    """Single benchmark evaluation case."""

    case_id: str
    workspace_fixture: str
    question: str
    expected_source_documents: list[str]
    expected_answer_signals: list[str]
    expected_response_mode: str  # "answer_from_context" | "refuse_out_of_scope" | "insufficient_context"

    # optional
    expected_source_chunks: list[str] = field(default_factory=list)
    filters: dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvalCase":
        return cls(
            case_id=data["case_id"],
            workspace_fixture=data["workspace_fixture"],
            question=data["question"],
            expected_source_documents=data["expected_source_documents"],
            expected_answer_signals=data.get("expected_answer_signals", []),
            expected_response_mode=data.get("expected_response_mode", "answer_from_context"),
            expected_source_chunks=data.get("expected_source_chunks", []),
            filters=data.get("filters", {}),
            notes=data.get("notes", ""),
            tags=data.get("tags", []),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "workspace_fixture": self.workspace_fixture,
            "question": self.question,
            "expected_source_documents": self.expected_source_documents,
            "expected_answer_signals": self.expected_answer_signals,
            "expected_response_mode": self.expected_response_mode,
            "expected_source_chunks": self.expected_source_chunks,
            "filters": self.filters,
            "notes": self.notes,
            "tags": self.tags,
        }

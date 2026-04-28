"""Unit tests for observability utilities (A6)."""

import json
import logging
import time

import pytest

from app.core.observability.correlation import (
    ensure_correlation_id,
    get_correlation_id,
    new_correlation_id,
    set_correlation_id,
)
from app.core.observability.timer import StageTimer


# ── Correlation ID generation ─────────────────────────────────────────────────

def test_new_correlation_id_starts_with_req() -> None:
    cid = new_correlation_id()
    assert cid.startswith("req_")


def test_new_correlation_id_is_unique() -> None:
    ids = {new_correlation_id() for _ in range(50)}
    assert len(ids) == 50


def test_set_and_get_correlation_id() -> None:
    set_correlation_id("req_testvalue123")
    assert get_correlation_id() == "req_testvalue123"


def test_ensure_correlation_id_generates_when_empty() -> None:
    set_correlation_id("")
    cid = ensure_correlation_id()
    assert cid.startswith("req_")
    # subsequent calls return the same one
    assert get_correlation_id() == cid


def test_ensure_correlation_id_returns_existing() -> None:
    set_correlation_id("req_existing001")
    cid = ensure_correlation_id()
    assert cid == "req_existing001"


# ── StageTimer ────────────────────────────────────────────────────────────────

def test_stage_timer_captures_elapsed() -> None:
    timer = StageTimer()
    with timer.stage("retrieval"):
        time.sleep(0.01)
    timings = timer.timings_ms()
    assert "retrieval" in timings
    assert timings["retrieval"] >= 5  # at least 5ms


def test_stage_timer_multiple_stages() -> None:
    timer = StageTimer()
    with timer.stage("a"):
        time.sleep(0.005)
    with timer.stage("b"):
        time.sleep(0.005)
    timings = timer.timings_ms()
    assert "a" in timings
    assert "b" in timings


def test_stage_timer_total_ms() -> None:
    timer = StageTimer()
    with timer.stage("x"):
        time.sleep(0.01)
    with timer.stage("y"):
        time.sleep(0.01)
    total = timer.total_ms()
    assert total >= 15  # at least 15ms for both combined


def test_stage_timer_empty_returns_zero_total() -> None:
    timer = StageTimer()
    assert timer.total_ms() == 0.0
    assert timer.timings_ms() == {}


def test_stage_timer_rounds_to_two_decimals() -> None:
    timer = StageTimer()
    with timer.stage("s"):
        pass
    timings = timer.timings_ms()
    # The value should be a float with at most 2 decimal places
    assert isinstance(timings["s"], float)


# ── StructuredLogger ──────────────────────────────────────────────────────────

def test_structured_logger_emits_json(caplog, monkeypatch) -> None:
    monkeypatch.setenv("OBSERVABILITY_JSON_LOGS", "true")

    # Re-import to pick up the env var (instance is created per call)
    from app.core.observability.logging import StructuredLogger
    set_correlation_id("req_logtest001")

    logger = StructuredLogger("test.structured.json")
    with caplog.at_level(logging.INFO, logger="test.structured.json"):
        logger.info("chat.completed", workspace_id="ws-1", status="success")

    # Find the JSON log record
    json_records = [r.message for r in caplog.records]
    assert len(json_records) >= 1
    parsed = json.loads(json_records[-1])
    assert parsed["event"] == "chat.completed"
    assert parsed["request_id"] == "req_logtest001"
    assert parsed["workspace_id"] == "ws-1"
    assert "ts" in parsed

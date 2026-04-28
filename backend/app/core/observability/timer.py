"""
Stage timer utility for capturing step-level latency (A6).

Usage:
    timer = StageTimer()
    with timer.stage("retrieval"):
        ...
    with timer.stage("reranking"):
        ...
    timings = timer.timings_ms()  # {"retrieval": 104.2, "reranking": 57.3}
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Generator


class StageTimer:
    """Captures durations for named stages."""

    def __init__(self) -> None:
        self._start: dict[str, float] = {}
        self._elapsed: dict[str, float] = {}

    @contextmanager
    def stage(self, name: str) -> Generator[None, None, None]:
        start = time.monotonic()
        try:
            yield
        finally:
            self._elapsed[name] = (time.monotonic() - start) * 1000

    def timings_ms(self) -> dict[str, float]:
        return {k: round(v, 2) for k, v in self._elapsed.items()}

    def total_ms(self) -> float:
        return round(sum(self._elapsed.values()), 2)

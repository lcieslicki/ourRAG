"""
Structured logging helper with correlation ID binding (A6).

Emits JSON logs when OBSERVABILITY_JSON_LOGS=true,
otherwise falls back to standard Python logging.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from app.core.observability.correlation import get_correlation_id


class StructuredLogger:
    """
    Thin wrapper around Python's logging that injects correlation_id
    and emits structured JSON when configured.
    """

    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)
        self._json = os.environ.get("OBSERVABILITY_JSON_LOGS", "true").lower() == "true"

    def info(self, event: str, **kwargs: Any) -> None:
        self._emit(logging.INFO, event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        self._emit(logging.WARNING, event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        self._emit(logging.ERROR, event, **kwargs)

    def debug(self, event: str, **kwargs: Any) -> None:
        self._emit(logging.DEBUG, event, **kwargs)

    def _emit(self, level: int, event: str, **kwargs: Any) -> None:
        if not self._logger.isEnabledFor(level):
            return

        cid = get_correlation_id()

        if self._json:
            record: dict[str, Any] = {
                "ts": datetime.now(UTC).isoformat(),
                "level": logging.getLevelName(level).lower(),
                "event": event,
                "request_id": cid,
                **kwargs,
            }
            self._logger.log(level, json.dumps(record, ensure_ascii=False, default=str))
        else:
            parts = [f"event={event}"]
            if cid:
                parts.append(f"request_id={cid}")
            for k, v in kwargs.items():
                parts.append(f"{k}={v!r}")
            self._logger.log(level, " ".join(parts))


def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)

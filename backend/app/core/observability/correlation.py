"""
Correlation ID generation and context propagation.
Uses contextvars to propagate request_id across the async call chain.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def new_correlation_id() -> str:
    return f"req_{uuid.uuid4().hex[:16]}"


def set_correlation_id(value: str) -> None:
    _correlation_id.set(value)


def get_correlation_id() -> str:
    return _correlation_id.get() or ""


def ensure_correlation_id() -> str:
    """Get or generate a correlation ID for the current context."""
    cid = _correlation_id.get()
    if not cid:
        cid = new_correlation_id()
        _correlation_id.set(cid)
    return cid

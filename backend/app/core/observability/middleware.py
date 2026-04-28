"""
FastAPI middleware for assigning correlation IDs to all requests (A6).

Reads X-Request-ID header if present, otherwise generates a new one.
Sets it in context var and echoes it back in the response header.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.observability.correlation import new_correlation_id, set_correlation_id

CORRELATION_HEADER = "X-Request-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(CORRELATION_HEADER) or new_correlation_id()
        set_correlation_id(request_id)

        response = await call_next(request)
        response.headers[CORRELATION_HEADER] = request_id
        return response

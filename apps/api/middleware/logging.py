import logging
import time
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger("meetingos.access")


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Production access logging middleware with Correlation ID and credential sanitization."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        # Attach request_id to request state
        request.state.request_id = request_id

        t0 = time.perf_counter()
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path

        try:
            response = await call_next(request)
            lat_ms = (time.perf_counter() - t0) * 1000
            response.headers["X-Request-ID"] = request_id

            logger.info(
                f"[{request_id}] {method} {path} status={response.status_code} "
                f"latency={lat_ms:.2f}ms client={client_ip}"
            )
            return response
        except Exception as exc:
            lat_ms = (time.perf_counter() - t0) * 1000
            logger.error(
                f"[{request_id}] {method} {path} status=500 "
                f"latency={lat_ms:.2f}ms client={client_ip} error={type(exc).__name__}"
            )
            raise

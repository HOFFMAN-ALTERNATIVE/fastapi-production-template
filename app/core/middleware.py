import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.requests import Request
from starlette.responses import Response

log = structlog.get_logger("app.request")


async def request_context_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Bind a request id to every log line and emit one structured access log per request."""
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    log.info(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round((time.perf_counter() - start) * 1000, 2),
    )
    return response

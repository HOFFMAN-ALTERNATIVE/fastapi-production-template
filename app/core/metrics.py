import time

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "route", "status"])
LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)


class PrometheusMiddleware:
    """Pure ASGI middleware. Labels use the matched route *template* (/items/{item_id})
    instead of the raw path, which keeps label cardinality bounded."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] == "/metrics":
            await self.app(scope, receive, send)
            return
        status = 500
        start = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            template = route_template(scope)
            method = scope["method"]
            LATENCY.labels(method, template).observe(time.perf_counter() - start)
            REQUESTS.labels(method, template, str(status)).inc()


def route_template(scope: Scope) -> str:
    """/api/v1/items/3f2a... -> /api/v1/items/{item_id}; unrouted paths collapse to 'unmatched'."""
    if scope.get("route") is None:
        return "unmatched"
    path = str(scope["path"])
    for name, value in (scope.get("path_params") or {}).items():
        path = path.replace(f"/{value}", f"/{{{name}}}")
    return path


def metrics_endpoint() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

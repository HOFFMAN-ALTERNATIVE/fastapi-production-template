# 0003. Prometheus metrics from a pure ASGI middleware, labelled by route template

Status: accepted
Date: 2026-10-17

## Context
Every service needs request counts and latency by endpoint. Labelling by raw path
turns `/items/<uuid>` into one time series per item, which grows without bound and
eventually hurts Prometheus. Starlette's `BaseHTTPMiddleware` also has known issues
with streaming responses and background tasks.

## Options
1. A third-party instrumentator package: quick, but one more dependency whose label
   choices and defaults we would have to audit anyway.
2. `BaseHTTPMiddleware` with the raw path: short code, unbounded cardinality.
3. A small pure ASGI middleware that wraps `send`, records status and latency, and
   labels by the matched route template. Unmatched paths collapse to `unmatched`.

## Decision
Option 3. About 50 lines of code give bounded labels and no dependency beyond
`prometheus_client`.

## Consequences
- Series count is bounded by routes times methods times status codes.
- 404 scans from bots land in one `unmatched` series instead of thousands.
- The template is rebuilt by replacing path parameter values in the path. A value that
  also appears in a static segment could be replaced in the wrong place.
- The container starts two uvicorn workers by default and `prometheus_client` is not in
  multiprocess mode, so each scrape sees only the worker that answered. Set
  `WORKERS=1` or enable multiprocess mode before relying on the numbers.

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, health, items
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.metrics import PrometheusMiddleware, mark_worker_dead, metrics_endpoint
from app.core.middleware import request_context_middleware
from app.db.session import engine
from app.services.redis import get_redis


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    log = structlog.get_logger("app")
    log.info("startup", environment=get_settings().environment)
    yield
    await get_redis().aclose()
    await engine.dispose()
    mark_worker_dead()
    log.info("shutdown")


def create_app() -> FastAPI:
    s = get_settings()
    configure_logging(s.log_level, s.log_json)
    app = FastAPI(
        title=s.app_name,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if s.environment != "production" else None,
        redoc_url=None,
    )
    app.add_middleware(PrometheusMiddleware)
    app.middleware("http")(request_context_middleware)
    if s.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=s.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    api = APIRouter(prefix="/api/v1")
    api.include_router(auth.router)
    api.include_router(items.router)
    app.include_router(api)
    app.include_router(health.router)
    app.add_api_route("/metrics", metrics_endpoint, include_in_schema=False)
    return app


app = create_app()

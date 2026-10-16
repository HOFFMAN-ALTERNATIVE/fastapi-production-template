from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.api.deps import SessionDep
from app.services.redis import get_redis

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def live() -> dict[str, str]:
    """Liveness: the process is up."""
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(session: SessionDep, response: Response) -> dict[str, str]:
    """Readiness: dependencies reachable."""
    checks: dict[str, str] = {}
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
    try:
        await get_redis().ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"
    healthy = all(v == "ok" for v in checks.values())
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ok" if healthy else "degraded", **checks}

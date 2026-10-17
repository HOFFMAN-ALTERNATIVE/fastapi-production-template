import pytest
from httpx import AsyncClient
from pydantic import SecretStr, ValidationError

from app.core.config import Settings


async def test_liveness(client: AsyncClient) -> None:
    r = await client.get("/health/live")
    assert r.json() == {"status": "ok"}


async def test_readiness(client: AsyncClient) -> None:
    r = await client.get("/health/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "ok", "redis": "ok"}


async def test_request_id_propagated(client: AsyncClient) -> None:
    r = await client.get("/health/live", headers={"x-request-id": "abc123"})
    assert r.headers["x-request-id"] == "abc123"
    assert len((await client.get("/health/live")).headers["x-request-id"]) == 32


async def test_metrics_use_route_templates(client: AsyncClient) -> None:
    await client.get("/api/v1/items/00000000-0000-0000-0000-000000000000")
    body = (await client.get("/metrics")).text
    assert "http_requests_total" in body
    assert 'route="/api/v1/items/{item_id}"' in body
    assert "00000000-0000" not in body


@pytest.mark.parametrize(
    "secret", ["change-me", "CHANGE_ME_TO_A_LONG_RANDOM_STRING", "short-but-not-placeholder"]
)
def test_production_rejects_weak_jwt_secret(secret: str) -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(environment="production", jwt_secret=SecretStr(secret))


def test_production_accepts_long_random_secret() -> None:
    s = Settings(environment="production", jwt_secret=SecretStr("k" * 40))
    assert s.environment == "production"

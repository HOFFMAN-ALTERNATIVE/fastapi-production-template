from httpx import AsyncClient


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

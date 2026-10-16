from httpx import AsyncClient

from tests.conftest import register_and_login


async def test_crud(client: AsyncClient) -> None:
    h = await register_and_login(client)
    r = await client.post("/api/v1/items", json={"title": "First", "description": "x"}, headers=h)
    assert r.status_code == 201
    item = r.json()

    r = await client.patch(f"/api/v1/items/{item['id']}", json={"title": "Renamed"}, headers=h)
    assert r.status_code == 200
    assert r.json()["title"] == "Renamed"
    assert r.json()["description"] == "x"

    r = await client.get(f"/api/v1/items/{item['id']}", headers=h)
    assert r.json()["title"] == "Renamed"

    assert (await client.delete(f"/api/v1/items/{item['id']}", headers=h)).status_code == 204
    assert (await client.get(f"/api/v1/items/{item['id']}", headers=h)).status_code == 404


async def test_pagination(client: AsyncClient) -> None:
    h = await register_and_login(client)
    for i in range(5):
        await client.post("/api/v1/items", json={"title": f"item {i}"}, headers=h)
    page = (await client.get("/api/v1/items?limit=2&offset=1", headers=h)).json()
    assert page["total"] == 5
    assert len(page["items"]) == 2
    assert (await client.get("/api/v1/items?limit=1000", headers=h)).status_code == 422


async def test_isolation_between_users(client: AsyncClient) -> None:
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    item = (await client.post("/api/v1/items", json={"title": "secret"}, headers=alice)).json()
    assert (await client.get(f"/api/v1/items/{item['id']}", headers=bob)).status_code == 404
    assert (await client.delete(f"/api/v1/items/{item['id']}", headers=bob)).status_code == 404
    assert (await client.get("/api/v1/items", headers=bob)).json()["total"] == 0


async def test_requires_auth(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/items")).status_code == 401

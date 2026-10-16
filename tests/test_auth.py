from httpx import AsyncClient

from app.core.security import create_token
from tests.conftest import register_and_login


async def test_register_login_me(client: AsyncClient) -> None:
    headers = await register_and_login(client)
    r = await client.get("/api/v1/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "ada@example.com"
    assert "hashed_password" not in r.json()


async def test_duplicate_email_conflict(client: AsyncClient) -> None:
    body = {"email": "Dup@Example.com", "password": "password123"}
    assert (await client.post("/api/v1/auth/register", json=body)).status_code == 201
    body["email"] = "dup@example.com"
    assert (await client.post("/api/v1/auth/register", json=body)).status_code == 409


async def test_register_validation(client: AsyncClient) -> None:
    r = await client.post("/api/v1/auth/register", json={"email": "nope", "password": "short"})
    assert r.status_code == 422


async def test_wrong_password(client: AsyncClient) -> None:
    await register_and_login(client)
    r = await client.post(
        "/api/v1/auth/login", data={"username": "ada@example.com", "password": "wrong-password"}
    )
    assert r.status_code == 401


async def test_login_rate_limited(client: AsyncClient) -> None:
    await register_and_login(client)
    codes = []
    for _ in range(7):
        r = await client.post(
            "/api/v1/auth/login", data={"username": "ada@example.com", "password": "bad-password"}
        )
        codes.append(r.status_code)
    assert codes[:5] == [401] * 5
    assert codes[5] == 429
    assert int(r.headers["retry-after"]) > 0


async def test_refresh_flow(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register", json={"email": "r@example.com", "password": "password123"}
    )
    tokens = (
        await client.post(
            "/api/v1/auth/login", data={"username": "r@example.com", "password": "password123"}
        )
    ).json()
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    # an access token must not be accepted as a refresh token
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert r.status_code == 401


async def test_rejects_bad_and_wrong_type_tokens(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    bad = {"Authorization": "Bearer not-a-jwt"}
    assert (await client.get("/api/v1/auth/me", headers=bad)).status_code == 401
    refresh = create_token("00000000-0000-0000-0000-000000000000", "refresh")
    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh}"})
    assert r.status_code == 401

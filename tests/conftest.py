import os
from collections.abc import AsyncIterator

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET", "test-secret-please-change")
os.environ.setdefault("LOG_JSON", "false")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

import pytest
from fakeredis import FakeAsyncRedis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_session
from app.main import app
from app.services.redis import set_redis

TEST_DB = os.environ["DATABASE_URL"]


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(TEST_DB)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def client(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncClient]:
    async def _session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = _session
    redis = FakeAsyncRedis(decode_responses=True)
    set_redis(redis)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
    await redis.aclose()
    set_redis(None)


async def register_and_login(
    client: AsyncClient, email: str = "ada@example.com", password: str = "correct-horse-1"
) -> dict[str, str]:
    r = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    r = await client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}

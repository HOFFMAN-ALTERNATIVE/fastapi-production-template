from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


def build_engine(url: str | None = None) -> AsyncEngine:
    s = get_settings()
    url = url or s.database_url
    kwargs: dict[str, object] = {"pool_pre_ping": True}
    if not url.startswith("sqlite"):
        kwargs |= {"pool_size": s.db_pool_size, "max_overflow": s.db_max_overflow}
    return create_async_engine(url, **kwargs)


engine = build_engine()
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session

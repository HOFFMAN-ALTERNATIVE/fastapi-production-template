from redis.asyncio import Redis


class RateLimiter:
    """Fixed-window limiter backed by Redis INCR + EXPIRE (atomic via pipeline)."""

    def __init__(self, redis: Redis, limit: int, window_seconds: int, prefix: str = "rl") -> None:
        self.redis, self.limit, self.window, self.prefix = redis, limit, window_seconds, prefix

    async def hit(self, key: str) -> tuple[bool, int]:
        """Register a hit. Returns (allowed, retry_after_seconds)."""
        k = f"{self.prefix}:{key}"
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.incr(k)
            pipe.expire(k, self.window, nx=True)
            pipe.ttl(k)
            count, _, ttl = await pipe.execute()
        allowed = int(count) <= self.limit
        return allowed, 0 if allowed else max(int(ttl), 1)

    async def reset(self, key: str) -> None:
        await self.redis.delete(f"{self.prefix}:{key}")

from fakeredis import FakeAsyncRedis

from app.services.rate_limit import RateLimiter


async def test_fixed_window() -> None:
    rl = RateLimiter(FakeAsyncRedis(), limit=2, window_seconds=30)
    assert (await rl.hit("k"))[0]
    assert (await rl.hit("k"))[0]
    allowed, retry = await rl.hit("k")
    assert not allowed
    assert 0 < retry <= 30
    await rl.reset("k")
    assert (await rl.hit("k"))[0]

from redis.asyncio import Redis

from app.config import get_settings

settings = get_settings()

_redis: Redis | None = None


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def blacklist_token(jti: str, ttl_seconds: int) -> None:
    r = await get_redis()
    await r.set(f"blacklist:{jti}", "1", ex=ttl_seconds)


async def is_blacklisted(jti: str) -> bool:
    r = await get_redis()
    return bool(await r.exists(f"blacklist:{jti}"))

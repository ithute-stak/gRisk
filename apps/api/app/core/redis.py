from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from redis.asyncio import Redis

from app.core.config import get_settings

settings = get_settings()


def create_redis_client() -> Redis:
    return Redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )


@asynccontextmanager
async def redis_connection() -> AsyncIterator[Redis]:
    client = create_redis_client()
    try:
        yield client
    finally:
        await client.aclose()


# Long-lived application client retained for components that need process-lifetime
# ownership. Request-scoped operations should use redis_connection() so tests and
# other multi-loop environments never reuse a connection bound to another loop.
redis_client = create_redis_client()

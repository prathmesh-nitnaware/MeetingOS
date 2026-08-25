import logging

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


def get_redis_client(redis_url: str) -> aioredis.Redis:
    """Create an async Redis client."""
    return aioredis.from_url(redis_url, decode_responses=True)


async def check_redis_connection(redis_url: str) -> bool:
    """Perform a lightweight health check ping against Redis."""
    client: aioredis.Redis | None = None
    try:
        client = get_redis_client(redis_url)
        return bool(await client.ping())
    except Exception as exc:
        logger.warning("Redis connectivity check failed: %s", exc)
        return False
    finally:
        if client is not None:
            await client.aclose()

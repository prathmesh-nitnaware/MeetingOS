import time

import redis
from fastapi import HTTPException, Request, status

# Local in-memory sliding-window fallback cache
in_memory_cache: dict[str, list[float]] = {}


class RateLimiter:
    """Sliding-window rate limiter using Redis with memory fallback."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.redis_client = None

        try:
            # Connect to default redis configuration
            self.redis_client = redis.Redis(
                host="localhost", port=6379, db=0, socket_timeout=0.5, socket_connect_timeout=0.5
            )
            self.redis_client.ping()
        except Exception:
            # Fall back to in-memory tracking if Redis is offline
            self.redis_client = None

    def is_allowed(self, key: str) -> bool:
        now = time.time()

        if self.redis_client:
            try:
                pipe = self.redis_client.pipeline()
                # Clear timestamps older than the sliding window boundary
                pipe.zremrangebyscore(key, 0, now - self.window_seconds)
                # Add current request score/timestamp
                pipe.zadd(key, {str(now): now})
                # Count current window volume
                pipe.zcard(key)
                # Refresh sliding window expiration
                pipe.expire(key, self.window_seconds)
                res = pipe.execute()
                count = res[2]
                return count <= self.limit
            except Exception:
                # Redis failure fallback to local memory
                pass

        # In-memory sliding-window fallback
        if key not in in_memory_cache:
            in_memory_cache[key] = []

        # Filter timestamps outside window
        cutoff = now - self.window_seconds
        in_memory_cache[key] = [ts for ts in in_memory_cache[key] if ts > cutoff]
        in_memory_cache[key].append(now)

        return len(in_memory_cache[key]) <= self.limit


def rate_limit(limit: int, window_seconds: int = 60):
    """FastAPI route dependency to limit endpoint requests."""
    limiter = RateLimiter(limit, window_seconds)

    def rate_limit_dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        # Key unique to client IP and request endpoint
        key = f"rl:{request.url.path}:{client_ip}"

        if not limiter.is_allowed(key):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Rate limit exceeded.",
            )

    return rate_limit_dependency

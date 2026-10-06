import hashlib
import threading
import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

import redis
import redis.asyncio as aioredis
from fastapi import HTTPException, Request, status

# Local in-memory sliding-window fallback cache (per process)
in_memory_cache: dict[str, list[float]] = {}
_memory_lock = threading.Lock()

# After a Redis failure, wait this long before trying Redis again
_REDIS_RETRY_SECONDS = 30.0


class RateLimiter:
    """Sliding-window rate limiter using Redis when reachable, with an in-memory fallback."""

    def __init__(self, limit: int, window_seconds: int = 60, redis_url: str | None = None) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.redis_url = redis_url
        self._sync_client: redis.Redis | None = None
        self._async_client: aioredis.Redis | None = None
        self._redis_failed_at = 0.0

    # ------------------------------------------------------------------ helpers

    def _redis_usable(self) -> bool:
        return bool(self.redis_url) and time.time() - self._redis_failed_at > _REDIS_RETRY_SECONDS

    def _memory_hit(self, key: str, now: float) -> bool:
        cutoff = now - self.window_seconds
        with _memory_lock:
            window = [ts for ts in in_memory_cache.get(key, []) if ts > cutoff]
            if len(window) >= self.limit:
                in_memory_cache[key] = window
                return False
            window.append(now)
            in_memory_cache[key] = window
            return True

    # --------------------------------------------------------------- public API

    def is_allowed(self, key: str) -> bool:
        """Synchronous check (used by scripts/tests). Rejected requests are not counted."""
        now = time.time()
        if self._redis_usable():
            try:
                if self._sync_client is None:
                    self._sync_client = redis.Redis.from_url(
                        self.redis_url or "", socket_timeout=0.5, socket_connect_timeout=0.5
                    )
                pipe = self._sync_client.pipeline()
                pipe.zremrangebyscore(key, 0, now - self.window_seconds)
                pipe.zcard(key)
                _, count = pipe.execute()
                if count >= self.limit:
                    return False
                self._sync_client.zadd(key, {f"{now}:{uuid4().hex}": now})
                self._sync_client.expire(key, self.window_seconds)
                return True
            except Exception:
                self._sync_client = None
                self._redis_failed_at = now
        return self._memory_hit(key, now)

    async def is_allowed_async(self, key: str) -> bool:
        """Non-blocking check used inside request handlers."""
        now = time.time()
        if self._redis_usable():
            try:
                if self._async_client is None:
                    self._async_client = aioredis.from_url(
                        self.redis_url or "", socket_timeout=0.5, socket_connect_timeout=0.5
                    )
                pipe = self._async_client.pipeline()
                pipe.zremrangebyscore(key, 0, now - self.window_seconds)
                pipe.zcard(key)
                _, count = await pipe.execute()
                if count >= self.limit:
                    return False
                await self._async_client.zadd(key, {f"{now}:{uuid4().hex}": now})
                await self._async_client.expire(key, self.window_seconds)
                return True
            except Exception:
                self._async_client = None
                self._redis_failed_at = now
        return self._memory_hit(key, now)


_limiters: dict[tuple[str, int, str], RateLimiter] = {}


def _caller_key(request: Request) -> str:
    """Identify the caller by bearer token (hashed) or, when anonymous, by client IP."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer ") and auth[7:].strip():
        return "tok:" + hashlib.sha256(auth[7:].strip().encode("utf-8")).hexdigest()[:24]
    host = request.client.host if request.client else "unknown"
    return f"ip:{host}"


def rate_limit(bucket: str, per_minute: Callable[[], int]) -> Callable[[Request], Awaitable[None]]:
    """FastAPI dependency factory enforcing ``per_minute()`` requests per caller per minute."""

    async def dependency(request: Request) -> None:
        from apps.api.config import settings

        if not settings.rate_limiting_enabled:
            return
        limit = per_minute()
        cache_key = (bucket, limit, settings.redis_url)
        limiter = _limiters.get(cache_key)
        if limiter is None:
            limiter = RateLimiter(limit=limit, window_seconds=60, redis_url=settings.redis_url)
            _limiters[cache_key] = limiter

        if not await limiter.is_allowed_async(
            f"meetingos:ratelimit:{bucket}:{_caller_key(request)}"
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests. The limit for this action is {limit} per minute.",
                headers={"Retry-After": "60"},
            )

    return dependency

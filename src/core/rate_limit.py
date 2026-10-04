import time
import logging
from fastapi import HTTPException
import redis.asyncio as redis

from src.core.config import settings
from typing import Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(
        self, redis_url: Optional[str] = None, limit: Optional[int] = None, window_secs: Optional[int] = None
    ):
        self.limit = limit or settings.rate_limit_requests
        self.window_secs = window_secs or settings.rate_limit_window_secs
        self.redis_url = redis_url or settings.redis_url
        self._client = None
        self._redis_available = False
        # Fallback in-memory store for when Redis is unavailable
        self._memory_store = {}  # type: ignore

    async def _get_client(self):
        if self._client is None:
            try:
                self._client = redis.from_url(self.redis_url, decode_responses=True)
                # Test connection
                await self._client.ping()
                self._redis_available = True
                logger.info("Redis connection established for rate limiting")
            except Exception as e:
                logger.warning(f"Redis unavailable, using in-memory rate limiting: {e}")
                self._redis_available = False
                self._client = None
        return self._client

    async def check_rate_limit(self, farmer_id: str, client_ip: Optional[str] = None) -> bool:
        """
        Check if a farmer (by phone number) has exceeded the rate limit.
        Uses a sliding window algorithm with Redis sorted sets when available,
        falls back to in-memory store.
        """
        client = await self._get_client()
        now = time.time()
        window_start = now - self.window_secs

        # Primary bucket: per farmer_id (phone number)
        farmer_key = f"ratelimit:farmer:{farmer_id}"

        # Secondary bucket: per IP (for requests before farmer_id is known)
        ip_key = f"ratelimit:ip:{client_ip}" if client_ip else None

        if self._redis_available and client:
            # Use Redis
            try:
                # Check farmer bucket
                farmer_count = await self._check_bucket_redis(
                    client, farmer_key, window_start, now
                )
                if farmer_count >= self.limit:
                    logger.warning(
                        f"Rate limit exceeded for farmer {farmer_id}: {farmer_count}/{self.limit}"
                    )
                    raise HTTPException(
                        status_code=429,
                        detail=f"Rate limit exceeded. Try again in {self.window_secs} seconds.",
                    )

                # Check IP bucket (if applicable)
                if ip_key:
                    ip_count = await self._check_bucket_redis(
                        client, ip_key, window_start, now
                    )
                    if ip_count >= self.limit:
                        logger.warning(
                            f"Rate limit exceeded for IP {client_ip}: {ip_count}/{self.limit}"
                        )
                        raise HTTPException(
                            status_code=429,
                            detail=f"Rate limit exceeded. Try again in {self.window_secs} seconds.",
                        )
                return True
            except Exception as e:
                logger.warning(
                    f"Redis error during rate limit check, falling back to memory: {e}"
                )
                self._redis_available = False
                # Fall through to memory store

        # Fallback: in-memory store
        return self._check_bucket_memory(farmer_key, window_start, now, ip_key)

    async def _check_bucket_redis(
        self, client, key: str, window_start: float, now: float
    ) -> int:
        """
        Sliding window rate limit using Redis sorted set.
        Adds current request, removes expired entries, returns count.
        """
        pipe = client.pipeline()
        # Add current request with timestamp as score
        pipe.zadd(key, {str(now): now})
        # Remove expired entries
        pipe.zremrangebyscore(key, 0, window_start)
        # Count current entries
        pipe.zcard(key)
        # Set expiry on key (window_secs + buffer)
        pipe.expire(key, self.window_secs + 10)
        results = await pipe.execute()
        return results[2]  # zcard result

    def _check_bucket_memory(
        self, farmer_key: str, window_start: float, now: float, ip_key: Optional[str] = None
    ) -> bool:
        """In-memory fallback rate limiting."""
        # Clean expired entries
        self._cleanup_memory(window_start)

        # Check farmer bucket
        farmer_count = len(self._memory_store.get(farmer_key, []))
        if farmer_count >= self.limit:
            logger.warning(
                f"Rate limit exceeded (memory) for farmer {farmer_key}: {farmer_count}/{self.limit}"
            )
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Try again in {self.window_secs} seconds.",
            )

        # Add current request
        if farmer_key not in self._memory_store:
            self._memory_store[farmer_key] = []
        self._memory_store[farmer_key].append(now)

        # Check IP bucket
        if ip_key:
            ip_count = len(self._memory_store.get(ip_key, []))
            if ip_count >= self.limit:
                logger.warning(
                    f"Rate limit exceeded (memory) for IP {ip_key}: {ip_count}/{self.limit}"
                )
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Try again in {self.window_secs} seconds.",
                )
            if ip_key not in self._memory_store:
                self._memory_store[ip_key] = []
            self._memory_store[ip_key].append(now)

        return True

    def _cleanup_memory(self, window_start: float):
        """Remove expired entries from memory store."""
        for key in list(self._memory_store.keys()):
            self._memory_store[key] = [
                ts for ts in self._memory_store[key] if ts > window_start
            ]
            if not self._memory_store[key]:
                del self._memory_store[key]

    async def close(self):
        if self._client:
            await self._client.close()


# Global instance
rate_limiter = RateLimiter()


async def get_rate_limiter() -> RateLimiter:
    """FastAPI dependency to get the rate limiter instance."""
    return rate_limiter

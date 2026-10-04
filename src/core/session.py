import logging
import redis.asyncio as redis

from src.core.config import settings
from typing import Optional

logger = logging.getLogger(__name__)


class SessionManager:
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.redis_url
        self._client = None
        self._redis_available = False
        # Fallback in-memory store
        self._memory_store = {}  # type: ignore
        # TTL for session data (24 hours)
        self.session_ttl = 86400

    async def _get_client(self):
        if self._client is None:
            try:
                self._client = redis.from_url(self.redis_url, decode_responses=True)
                # Test connection
                await self._client.ping()
                self._redis_available = True
                logger.info("Redis connection established for session management")
            except Exception as e:
                logger.warning(f"Redis unavailable, using in-memory session store: {e}")
                self._redis_available = False
                self._client = None
        return self._client

    async def increment_failure_count(self, farmer_id: str) -> int:
        """
        Increments the failure count for a farmer's current session.
        Returns the new failure count.
        """
        key = f"session_failures:{farmer_id}"
        client = await self._get_client()

        if self._redis_available and client:
            try:
                # Use Redis INCR with expiry
                count = await client.incr(key)
                if count == 1:
                    # Set expiry only on first increment
                    await client.expire(key, self.session_ttl)
                return count
            except Exception as e:
                logger.warning(
                    f"Redis error during increment_failure_count, falling back to memory: {e}"
                )
                self._redis_available = False
                # Fall through to memory store

        # Fallback: in-memory store
        count = self._memory_store.get(key, 0) + 1
        self._memory_store[key] = count
        return count

    def reset_failure_count(self, farmer_id: str):
        """
        Resets the failure count after a successful classification or fallback.
        """
        key = f"session_failures:{farmer_id}"

        # Try Redis first
        if self._redis_available and self._client:
            try:
                # This is async but we're in a sync method - we can't await here
                # Schedule the deletion for the next event loop iteration
                import asyncio

                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(self._client.delete(key))
                    else:
                        # If no running loop, just clean memory
                        if key in self._memory_store:
                            del self._memory_store[key]
                except RuntimeError:
                    # No event loop, clean memory
                    if key in self._memory_store:
                        del self._memory_store[key]
            except Exception:
                pass  # Ignore Redis errors, clean memory anyway

        # Always clean memory store
        if key in self._memory_store:
            del self._memory_store[key]

    async def get_failure_count(self, farmer_id: str) -> int:
        """Get current failure count without incrementing."""
        key = f"session_failures:{farmer_id}"
        client = await self._get_client()

        if self._redis_available and client:
            try:
                count = await client.get(key)
                return int(count) if count else 0
            except Exception:
                pass

        return self._memory_store.get(key, 0)

    async def close(self):
        if self._client:
            await self._client.close()


# Global instance
session_manager = SessionManager()

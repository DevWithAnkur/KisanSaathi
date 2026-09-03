import logging
import json
import redis.asyncio as redis
from typing import Optional

logger = logging.getLogger(__name__)

class RedisCache:
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        try:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None

    async def set_last_advisory(self, farmer_id: str, intent: str, text: str) -> bool:
        """
        Caches the last successfully generated advisory for a given farmer and intent.
        Expires in 48 hours to prevent serving severely stale data.
        """
        if not self.client:
            return False
            
        key = f"advisory:{farmer_id}:{intent}"
        try:
            # Store it for 48 hours (172800 seconds)
            await self.client.setex(key, 172800, text)
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    async def get_last_advisory(self, farmer_id: str, intent: str) -> Optional[str]:
        """
        Retrieves the last cached advisory if the active generation fails.
        """
        if not self.client:
            return None
            
        key = f"advisory:{farmer_id}:{intent}"
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

# Global instance to be used by the application
cache = RedisCache()

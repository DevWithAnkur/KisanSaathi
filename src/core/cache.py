import logging
import json
import redis.asyncio as redis
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class CachedAdvisory:
    """Represents a cached advisory with metadata."""
    def __init__(self, text: str, source_name: str, source_timestamp: datetime, 
                 cache_timestamp: datetime, cache_age_seconds: int):
        self.text = text
        self.source_name = source_name
        self.source_timestamp = source_timestamp
        self.cache_timestamp = cache_timestamp
        self.cache_age_seconds = cache_age_seconds
    
    def to_json(self) -> str:
        return json.dumps({
            "text": self.text,
            "source_name": self.source_name,
            "source_timestamp": self.source_timestamp.isoformat() if self.source_timestamp else None,
            "cache_timestamp": self.cache_timestamp.isoformat(),
            "cache_age_seconds": self.cache_age_seconds
        })
    
    @classmethod
    def from_json(cls, data: str) -> 'CachedAdvisory':
        obj = json.loads(data)
        return cls(
            text=obj["text"],
            source_name=obj["source_name"],
            source_timestamp=datetime.fromisoformat(obj["source_timestamp"]) if obj["source_timestamp"] else None,
            cache_timestamp=datetime.fromisoformat(obj["cache_timestamp"]),
            cache_age_seconds=obj["cache_age_seconds"]
        )


class RedisCache:
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        try:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None

    async def set_last_advisory(self, farmer_id: str, intent: str, text: str, 
                                source_name: str = None, source_timestamp: datetime = None) -> bool:
        """
        Caches the last successfully generated advisory for a given farmer and intent.
        Expires in 48 hours to prevent serving severely stale data.
        """
        if not self.client:
            return False
            
        key = f"advisory:{farmer_id}:{intent}"
        try:
            now = datetime.utcnow()
            source_ts = source_timestamp.isoformat() if source_timestamp else None
            cache_age = 0  # Fresh entry
            
            advisory = CachedAdvisory(
                text=text,
                source_name=source_name or "unknown",
                source_timestamp=source_timestamp,
                cache_timestamp=now,
                cache_age_seconds=cache_age
            )
            
            # Store it for 48 hours (172800 seconds)
            await self.client.setex(key, 172800, advisory.to_json())
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    async def get_last_advisory(self, farmer_id: str, intent: str) -> Optional[CachedAdvisory]:
        """
        Retrieves the last cached advisory if the active generation fails.
        Returns CachedAdvisory object with metadata.
        """
        if not self.client:
            return None
            
        key = f"advisory:{farmer_id}:{intent}"
        try:
            data = await self.client.get(key)
            if data:
                advisory = CachedAdvisory.from_json(data)
                # Update cache age
                advisory.cache_age_seconds = int((datetime.utcnow() - advisory.cache_timestamp).total_seconds())
                return advisory
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    async def compare_and_flag_conflict(self, farmer_id: str, intent: str, 
                                         fresh_text: str, fresh_source: str, fresh_timestamp: datetime,
                                         threshold: float = 0.15) -> Optional[str]:
        """
        Compare fresh data with cached data and return conflict message if significant discrepancy.
        Threshold is relative difference (15% default).
        """
        cached = await self.get_last_advisory(farmer_id, intent)
        if not cached:
            return None
            
        # For text-based advisories, we can check for specific numeric differences
        # This is a simplified check - in production, extract and compare numeric values
        conflict_msg = self._check_text_conflict(fresh_text, cached.text, fresh_source, cached.source_name)
        
        if conflict_msg:
            logger.warning(f"Data conflict detected for {farmer_id}/{intent}: {conflict_msg}")
            return conflict_msg
        
        return None
    
    def _check_text_conflict(self, fresh: str, cached: str, fresh_source: str, cached_source: str) -> Optional[str]:
        """
        Simple text-based conflict detection.
        Returns conflict message if sources differ significantly.
        """
        # If sources are the same, no conflict
        if fresh_source == cached_source:
            return None
            
        # Extract numbers from both texts for comparison
        import re
        fresh_numbers = [float(n) for n in re.findall(r'\d+(?:\.\d+)?', fresh)]
        cached_numbers = [float(n) for n in re.findall(r'\d+(?:\.\d+)?', cached)]
        
        if not fresh_numbers or not cached_numbers:
            return None
            
        # Compare first number found (e.g., price, temperature, amount)
        fresh_val = fresh_numbers[0]
        cached_val = cached_numbers[0]
        
        if cached_val == 0:
            return None
            
        diff_pct = abs(fresh_val - cached_val) / cached_val
        
        if diff_pct > 0.15:  # 15% threshold
            return (f"Data sources disagree: {fresh_source} shows {fresh_val}, "
                   f"{cached_source} (cached) showed {cached_val}. Showing latest.")
        
        return None


# Global instance to be used by the application
cache = RedisCache()
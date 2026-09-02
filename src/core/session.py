import redis
from src.core.config import settings

class SessionManager:
    def __init__(self):
        # In a real app, initialize with redis connection pool
        # self.redis = redis.from_url(settings.redis_url)
        self.mock_db = {} # using in-memory dict for mock

    def increment_failure_count(self, farmer_id: str) -> int:
        """
        Increments the failure count for a farmer's current session.
        Returns the new failure count.
        """
        key = f"session_failures:{farmer_id}"
        count = self.mock_db.get(key, 0) + 1
        self.mock_db[key] = count
        return count

    def reset_failure_count(self, farmer_id: str):
        """
        Resets the failure count after a successful classification or fallback.
        """
        key = f"session_failures:{farmer_id}"
        if key in self.mock_db:
            del self.mock_db[key]

session_manager = SessionManager()

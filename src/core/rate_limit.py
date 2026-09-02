from fastapi import HTTPException, Request

class RateLimiter:
    def __init__(self, limit: int = 10, window_secs: int = 60):
        self.limit = limit
        self.window_secs = window_secs
        # In a real app, use Redis for distributed rate limiting
        self.mock_db = {} 

    async def check_rate_limit(self, request: Request):
        """
        FastAPI dependency to check if a client has exceeded the rate limit.
        """
        # A simple mock based on client IP
        client_ip = request.client.host if request.client else "unknown"
        
        count = self.mock_db.get(client_ip, 0)
        if count >= self.limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
            
        self.mock_db[client_ip] = count + 1
        return True

rate_limiter = RateLimiter(limit=10, window_secs=60)

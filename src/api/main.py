from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging
from src.core.config import settings
from src.api.webhook import router as webhook_router
from src.api.ivr import router as ivr_router
from src.integrations import stt_client, tts_client, whatsapp_client
from src.core.database import init_db, engine
from src.core.database_iam import close_all_engines

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

class LatencyMiddleware(BaseHTTPMiddleware):
    """Middleware to measure request latency and log P50/P95 metrics."""
    
    def __init__(self, app, sample_rate: float = 1.0):
        super().__init__(app)
        self.sample_rate = sample_rate
        self.latencies = []  # Store latencies for percentile calculation
        self.max_samples = 10000  # Cap memory usage
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        
        # Process request
        response = await call_next(request)
        
        # Calculate latency
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        # Sample for metrics (to avoid memory issues in high traffic)
        import random
        if random.random() < self.sample_rate:
            self.latencies.append(latency_ms)
            if len(self.latencies) > self.max_samples:
                self.latencies = self.latencies[-self.max_samples:]
        
        # Add latency header for debugging
        response.headers["X-Response-Time-MS"] = f"{latency_ms:.2f}"
        
        # Log slow requests (>5s)
        if latency_ms > 5000:
            logger.warning(f"Slow request: {request.method} {request.url.path} took {latency_ms:.2f}ms")
        
        return response
    
    def get_percentiles(self) -> dict:
        """Calculate P50, P95, P99 latencies."""
        if not self.latencies:
            return {"p50": 0, "p95": 0, "p99": 0, "count": 0}
        
        sorted_latencies = sorted(self.latencies)
        n = len(sorted_latencies)
        
        def percentile(p):
            idx = int(n * p)
            return sorted_latencies[min(idx, n - 1)]
        
        return {
            "p50_ms": round(percentile(0.50), 2),
            "p95_ms": round(percentile(0.95), 2),
            "p99_ms": round(percentile(0.99), 2),
            "count": n,
            "max_ms": round(max(sorted_latencies), 2)
        }

# Global instance for metrics access
latency_middleware = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize clients
    logger.info("Initializing integration clients...")
    
    # Initialize database
    await init_db()
    
    # Initialize WhatsApp client with real credentials
    whatsapp_client.token = settings.whatsapp_api_token
    whatsapp_client.phone_number_id = settings.whatsapp_phone_number_id
    whatsapp_client.base_url = f"https://graph.facebook.com/v18.0/{settings.whatsapp_phone_number_id}"
    whatsapp_client.headers = {
        "Authorization": f"Bearer {settings.whatsapp_api_token}",
        "Content-Type": "application/json"
    }
    
    # Initialize STT/TTS clients with API keys
    stt_client.api_key = settings.asr_tts_api_key
    tts_client.api_key = settings.asr_tts_api_key
    
    logger.info("Integration clients initialized")
    
    yield
    
    # Shutdown: Close clients
    logger.info("Closing integration clients...")
    await stt_client.close()
    await tts_client.close()
    await whatsapp_client.close()
    if engine:
        await engine.dispose()
    # Close all IAM engines
    await close_all_engines()
    logger.info("Integration clients closed")

app = FastAPI(
    title="KisanSaathi API",
    description="Backend API for KisanSaathi Farmer Advisory Service",
    version="0.1.0",
    lifespan=lifespan
)

# Add latency middleware
latency_middleware = LatencyMiddleware(app, sample_rate=1.0)

app.include_router(webhook_router)
app.include_router(ivr_router)

@app.get("/health")
async def health_check():
    """Health check endpoint to verify API is running."""
    return {"status": "ok", "environment": settings.environment}

@app.get("/metrics/latency")
async def latency_metrics():
    """Endpoint to get latency percentiles."""
    return latency_middleware.get_percentiles()

@app.get("/disclaimer")
async def disclaimer(lang: str = "en"):
    """
    Return the legal disclaimer text.
    Query param: lang=en|hi
    """
    from src.agents.onboarding import LEGAL_DISCLAIMER, LEGAL_DISCLAIMER_HI
    
    if lang == "hi":
        return {"disclaimer": LEGAL_DISCLAIMER_HI, "language": "hi"}
    return {"disclaimer": LEGAL_DISCLAIMER, "language": "en"}
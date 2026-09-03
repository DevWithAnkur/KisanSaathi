from fastapi import FastAPI
from src.core.config import settings
from src.api.webhook import router as webhook_router
from src.api.ivr import router as ivr_router
import logging

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="KisanSaathi API",
    description="Backend API for KisanSaathi Farmer Advisory Service",
    version="0.1.0",
)

app.include_router(webhook_router)
app.include_router(ivr_router)

@app.get("/health")
async def health_check():
    """Health check endpoint to verify API is running."""
    return {"status": "ok", "environment": settings.environment}

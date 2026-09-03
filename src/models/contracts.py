from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class AgentRequest(BaseModel):
    farmer_id: str = Field(..., description="Phone number identifier of the farmer")
    session_id: str = Field(..., description="Session identifier for tracking fallbacks")
    message_id: str = Field(..., description="Unique message ID for idempotency")
    language: str = Field(..., description="Detected or preferred language (e.g., 'en', 'hi')")
    query_text: str = Field(..., description="Sanitized text or transcribed voice query")
    profile: Dict[str, Any] = Field(default_factory=dict, description="Farmer profile fields")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Request arrival time")
    correlation_id: str = Field(..., description="Log correlation ID")

class AgentResponse(BaseModel):
    text: str = Field(..., description="Short farmer-facing response text")
    audio_payload: Optional[str] = Field(default=None, description="Optional audio file URL or base64")
    agent_name: str = Field(..., description="Name of the agent that handled the request")
    intent: str = Field(..., description="Classified intent")
    source_name: Optional[str] = Field(default=None, description="Verified source name (e.g., PM-KISAN, Agmarknet)")
    source_reference: Optional[str] = Field(default=None, description="URL or ID of the source record")
    source_timestamp: Optional[datetime] = Field(default=None, description="When the source data was last updated")
    response_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Time response was generated")
    verification_status: str = Field(default="unverified", description="'verified', 'unverified', or 'failed'")
    cache_status: str = Field(default="miss", description="'hit' or 'miss'")
    cache_age_seconds: Optional[int] = Field(default=None, description="Age of cached data if cache_status is 'hit'")
    safe_fallback: bool = Field(default=False, description="True if response is a safe fallback due to error")


# Compatibility models for callers using the original climate contract names.
class ForecastData(BaseModel):
    max_temperature_c: Optional[float] = None
    total_rainfall_48h_mm: float = 0.0


class WeatherData(BaseModel):
    forecast: ForecastData
    source: str
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)

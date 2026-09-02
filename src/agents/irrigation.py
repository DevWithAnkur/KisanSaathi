import logging
from datetime import datetime
from typing import Optional

from ..models.contracts import AgentRequest, AgentResponse
from ..integrations.weather import WeatherClient

logger = logging.getLogger(__name__)

class IrrigationAgent:
    def __init__(self, weather_client: WeatherClient):
        self.weather_client = weather_client
        # Minimum rainfall in mm expected in 48h to recommend skipping irrigation
        self.rainfall_threshold_mm = 10.0

    async def process_request(self, request: AgentRequest) -> AgentResponse:
        lat = request.profile.get("latitude")
        lon = request.profile.get("longitude")

        # If we don't have location, we can't advise properly.
        if lat is None or lon is None:
            text = (
                "Please update your profile with your location "
                "so I can check the weather and advise on irrigation."
            )
            return self._build_response(
                request=request, 
                text=text, 
                verification_status="failed",
                safe_fallback=True
            )

        weather_data = await self.weather_client.get_48h_forecast(lat=lat, lon=lon)
        
        if not weather_data:
            text = (
                "I couldn't fetch the weather for your location right now. "
                "Please check the fields manually or try again later."
            )
            return self._build_response(
                request=request,
                text=text,
                verification_status="failed",
                safe_fallback=True
            )

        rainfall = weather_data.forecast.total_rainfall_48h_mm
        
        if rainfall > self.rainfall_threshold_mm:
            if request.language == "hi":
                text = f"अगले 48 घंटों में {rainfall} मिमी बारिश होने की संभावना है। आपको सिंचाई छोड़ देनी चाहिए।"
            else:
                text = f"There is a forecast of {rainfall} mm of rain in the next 48 hours. You should skip irrigation."
        else:
            if request.language == "hi":
                text = "आने वाले दिनों में बारिश की संभावना नहीं है। आपको अपनी फसल की सिंचाई करनी चाहिए।"
            else:
                text = "No significant rain is expected in the next few days. You should irrigate your crop."

        # Calculate cache age
        cache_age_seconds = None
        cache_status = "miss"
        if weather_data.retrieved_at:
            delta = datetime.utcnow() - weather_data.retrieved_at
            cache_age_seconds = int(delta.total_seconds())
            if cache_age_seconds > 60:  # If older than a minute, call it a hit
                cache_status = "hit"

        return self._build_response(
            request=request,
            text=text,
            source_name=weather_data.source,
            source_timestamp=weather_data.retrieved_at,
            verification_status="verified",
            cache_status=cache_status,
            cache_age_seconds=cache_age_seconds
        )

    def _build_response(self, request: AgentRequest, text: str, **kwargs) -> AgentResponse:
        return AgentResponse(
            text=text,
            agent_name="IrrigationAgent",
            intent="irrigation",
            response_timestamp=datetime.utcnow(),
            **kwargs
        )

import json
import logging
import os
from datetime import datetime
from typing import Optional

from ..models.contracts import AgentRequest, AgentResponse
from ..integrations.weather import WeatherClient

logger = logging.getLogger(__name__)

class SpoilageAgent:
    def __init__(self, weather_client: WeatherClient):
        self.weather_client = weather_client
        
        # Load shelf life data
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(current_dir, "..", "data", "shelf_life.json")
        try:
            with open(data_path, "r") as f:
                self.shelf_life_db = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load shelf_life.json: {e}")
            self.shelf_life_db = {}

    async def process_request(self, request: AgentRequest) -> AgentResponse:
        crop = request.profile.get("crop", "").lower()
        harvest_date_str = request.profile.get("harvest_date")
        lat = request.profile.get("latitude")
        lon = request.profile.get("longitude")

        # Validation
        if not crop or crop not in self.shelf_life_db:
            text = (
                "Please tell me which crop you have harvested so I can estimate its shelf life."
            )
            return self._build_response(request, text, safe_fallback=True)

        if not harvest_date_str:
            text = (
                "When did you harvest the crop? Please provide the harvest date to check spoilage risk."
            )
            return self._build_response(request, text, safe_fallback=True)

        if lat is None or lon is None:
            text = (
                "Please update your profile with your location "
                "so I can check the weather and advise on spoilage risk."
            )
            return self._build_response(request, text, safe_fallback=True)
            
        try:
            # Simple format: YYYY-MM-DD
            harvest_date = datetime.strptime(harvest_date_str, "%Y-%m-%d")
        except ValueError:
            text = "Invalid harvest date format. Please provide it as YYYY-MM-DD."
            return self._build_response(request, text, safe_fallback=True)

        weather_data = await self.weather_client.get_48h_forecast(lat=lat, lon=lon)
        
        if not weather_data:
            text = (
                "I couldn't fetch the weather for your location right now. "
                "Please check the fields manually or try again later."
            )
            return self._build_response(request, text, safe_fallback=True, verification_status="failed")

        # Baseline calculation
        baseline_days = self.shelf_life_db[crop]
        days_since_harvest = (datetime.utcnow() - harvest_date).days
        remaining_days = baseline_days - days_since_harvest
        
        # Weather heuristic impact
        avg_temp = None
        if weather_data.forecast.max_temperature_c is not None and weather_data.forecast.min_temperature_c is not None:
            avg_temp = (weather_data.forecast.max_temperature_c + weather_data.forecast.min_temperature_c) / 2
            
        avg_humidity = weather_data.forecast.average_humidity_percent

        if avg_temp and avg_humidity and avg_temp > 30.0 and avg_humidity > 70.0:
            # Cut remaining shelf life by 50% due to extreme heat and humidity
            remaining_days = remaining_days // 2

        # Risk Classification
        if remaining_days <= 0:
             alert_color = "Red"
             text_en = "Your crop has likely spoiled or is at extreme risk. Sell or move it immediately."
             text_hi = "आपकी फसल के खराब होने का भारी जोखिम है। इसे तुरंत बेचें या स्थानांतरित करें।"
        elif remaining_days < 3:
             alert_color = "Red"
             text_en = f"High spoilage risk (Red Alert). Sell within {remaining_days} days."
             text_hi = f"खराब होने का उच्च जोखिम (रेड अलर्ट)। {remaining_days} दिनों के भीतर बेचें।"
        elif remaining_days <= 7:
             alert_color = "Yellow"
             text_en = f"Moderate risk (Yellow Alert). You should plan to sell within {remaining_days} days."
             text_hi = f"मध्यम जोखिम (येलो अलर्ट)। आपको {remaining_days} दिनों के भीतर बेचने की योजना बनानी चाहिए।"
        else:
             alert_color = "Green"
             text_en = f"Safe to store (Green Alert). Estimated remaining shelf life is {remaining_days} days."
             text_hi = f"भंडारण के लिए सुरक्षित (ग्रीन अलर्ट)। अनुमानित शेष शेल्फ लाइफ {remaining_days} दिन है।"

        text = text_hi if request.language == "hi" else text_en

        cache_age_seconds = None
        cache_status = "miss"
        if weather_data.retrieved_at:
            delta = datetime.utcnow() - weather_data.retrieved_at
            cache_age_seconds = int(delta.total_seconds())
            if cache_age_seconds > 60:
                cache_status = "hit"

        return self._build_response(
            request=request,
            text=text,
            source_name=f"ShelfLifeDB + {weather_data.source}",
            source_timestamp=weather_data.retrieved_at,
            verification_status="verified",
            cache_status=cache_status,
            cache_age_seconds=cache_age_seconds
        )

    def _build_response(self, request: AgentRequest, text: str, **kwargs) -> AgentResponse:
        return AgentResponse(
            text=text,
            agent_name="SpoilageAgent",
            intent="spoilage",
            response_timestamp=datetime.utcnow(),
            **kwargs
        )

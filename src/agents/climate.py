import logging
from datetime import datetime

from ..models.contracts import AgentRequest, AgentResponse
from ..integrations.weather import WeatherClient

logger = logging.getLogger(__name__)

class ClimateAgent:
    def __init__(self, weather_client: WeatherClient):
        self.weather_client = weather_client

    async def process_request(self, request: AgentRequest) -> AgentResponse:
        lat = request.profile.get("latitude")
        lon = request.profile.get("longitude")
        
        # In a real scenario, we might use state/district to lookup lat/lon
        if lat is None or lon is None:
            # Fallback to hardcoded coords for MVP if state/district exist
            if request.profile.get("state"):
                lat, lon = 20.5937, 78.9629 # Central India mock
            else:
                text = "Please update your profile with your location so I can check for climate alerts." if request.language != "hi" else "कृपया अपना स्थान प्रोफ़ाइल में अपडेट करें ताकि मैं जलवायु अलर्ट की जांच कर सकूं।"
                return self._build_response(request, text, safe_fallback=True)

        weather_data = await self.weather_client.get_48h_forecast(lat=lat, lon=lon)
        
        if not weather_data:
             text = "I couldn't fetch the weather data for your region right now." if request.language != "hi" else "मुझे अभी आपके क्षेत्र का मौसम डेटा नहीं मिल सका।"
             return self._build_response(request, text, safe_fallback=True, verification_status="failed")

        # Anomaly Logic
        max_temp = weather_data.forecast.max_temperature_c
        total_rain = weather_data.forecast.total_rainfall_48h_mm
        
        alert_msg_en = ""
        alert_msg_hi = ""
        
        if max_temp and max_temp > 40.0:
            alert_msg_en += f"HEATWAVE WARNING: Temperatures are expected to reach {max_temp}°C. Ensure adequate irrigation and shade for sensitive crops. "
            alert_msg_hi += f"हीटवेव चेतावनी: तापमान {max_temp}°C तक पहुंचने की उम्मीद है। संवेदनशील फसलों के लिए पर्याप्त सिंचाई और छाया सुनिश्चित करें। "
            
        if total_rain and total_rain > 50.0:
            alert_msg_en += f"HEAVY RAIN WARNING: {total_rain}mm of rain is expected. Clear drainage channels to prevent waterlogging. "
            alert_msg_hi += f"भारी बारिश की चेतावनी: {total_rain} मिमी बारिश होने की उम्मीद है। जलभराव को रोकने के लिए जल निकासी चैनलों को साफ करें। "
            
        if not alert_msg_en:
            text_en = "There are currently no extreme climate alerts for your region."
            text_hi = "वर्तमान में आपके क्षेत्र के लिए कोई चरम जलवायु अलर्ट नहीं हैं।"
        else:
            text_en = alert_msg_en.strip()
            text_hi = alert_msg_hi.strip()
            
        text = text_hi if request.language == "hi" else text_en

        return self._build_response(
            request=request,
            text=text,
            source_name=weather_data.source,
            source_timestamp=weather_data.retrieved_at,
            verification_status="verified",
        )

    def _build_response(self, request: AgentRequest, text: str, **kwargs) -> AgentResponse:
        return AgentResponse(
            text=text,
            agent_name="ClimateAgent",
            intent="climate",
            response_timestamp=datetime.utcnow(),
            **kwargs
        )

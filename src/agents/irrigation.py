import logging
from datetime import datetime

from ..models.contracts import AgentRequest, AgentResponse
from ..integrations.weather import WeatherClient

logger = logging.getLogger(__name__)

# Energy benchmarks for pump energy estimation (FR-8a)
# Typical values - can be refined with local data
DIESEL_L_PER_HR_PER_HP = 0.7  # Liters of diesel per hour per HP
ELECTRIC_KWH_PER_HR_PER_HP = 0.75  # kWh per hour per HP
IRRIGATION_HOURS_PER_HECTARE = 4  # Typical hours to irrigate 1 hectare
WATER_VOLUME_L_PER_HECTARE = 50000  # Liters per hectare per irrigation (50mm depth)


class IrrigationAgent:
    def __init__(self, weather_client: WeatherClient):
        self.weather_client = weather_client
        # Minimum rainfall in mm expected in 48h to recommend skipping irrigation
        self.rainfall_threshold_mm = 10.0

    def _estimate_energy_saved(
        self, pump_type: str, motor_hp: float, land_size_ha: float
    ) -> dict:
        """
        Estimate energy saved by skipping one irrigation cycle.
        Returns dict with energy_saved and unit.
        """
        if not pump_type or not motor_hp or not land_size_ha:
            return None  # type: ignore

        # Total motor-hours for the irrigation
        total_motor_hours = IRRIGATION_HOURS_PER_HECTARE * land_size_ha

        pump_type = pump_type.lower().strip()

        if pump_type == "diesel":
            # Diesel consumption
            diesel_l = total_motor_hours * motor_hp * DIESEL_L_PER_HR_PER_HP
            return {
                "energy_saved": round(diesel_l, 2),
                "unit": "liters of diesel",
                "description": f"~{round(diesel_l, 1)} L diesel saved",
            }
        elif pump_type == "electric":
            # Electricity consumption
            kwh = total_motor_hours * motor_hp * ELECTRIC_KWH_PER_HR_PER_HP
            return {
                "energy_saved": round(kwh, 2),
                "unit": "kWh",
                "description": f"~{round(kwh, 1)} kWh electricity saved",
            }

        return None  # type: ignore

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
                safe_fallback=True,
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
                safe_fallback=True,
            )

        rainfall = weather_data.forecast.total_rainfall_48h_mm

        # Get pump info for energy estimate
        pump_type = request.profile.get("pump_type")
        motor_hp = request.profile.get("motor_hp")
        land_size_ha = request.profile.get("land_size_ha")

        # Convert land_size_ha if it's a string
        if land_size_ha is not None:
            try:
                land_size_ha = float(land_size_ha)
            except (ValueError, TypeError):
                land_size_ha = None

        energy_info = None
        if rainfall > self.rainfall_threshold_mm:
            if request.language == "hi":
                text = f"अगले 48 घंटों में {rainfall} मिमी बारिश होने की संभावना है। आपको सिंचाई छोड़ देनी चाहिए।"
            else:
                text = f"There is a forecast of {rainfall} mm of rain in the next 48 hours. You should skip irrigation."

            # Add energy estimate if pump info available
            energy_info = self._estimate_energy_saved(pump_type, motor_hp, land_size_ha)  # type: ignore
            if energy_info:
                if request.language == "hi":
                    text += f" इससे लगभग {energy_info['description']} होगी।"
                else:
                    text += f" This saves approximately {energy_info['description']}."
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
            cache_age_seconds=cache_age_seconds,
            energy_saved=energy_info,
        )

    def _build_response(
        self, request: AgentRequest, text: str, **kwargs
    ) -> AgentResponse:
        return AgentResponse(
            text=text,
            agent_name="IrrigationAgent",
            intent="irrigation",
            response_timestamp=datetime.utcnow(),
            **kwargs,
        )

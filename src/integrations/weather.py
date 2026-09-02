import httpx
import json
import logging
from typing import Optional
from datetime import datetime, timezone
import redis.asyncio as redis
from pydantic import ValidationError

from ..models.weather_models import WeatherForecast, CachedWeatherForecast

logger = logging.getLogger(__name__)

class WeatherClient:
    def __init__(self, redis_url: Optional[str] = None):
        # We use Open-Meteo as it doesn't require an API key for MVP
        self.base_url = "https://api.open-meteo.com/v1/forecast"
        self.redis = redis.from_url(redis_url) if redis_url else None
        self.cache_ttl_seconds = 3600  # 1 hour

    async def get_48h_forecast(self, lat: float, lon: float) -> Optional[CachedWeatherForecast]:
        """
        Fetches the 48h weather forecast for the given location.
        Tries to use cached data first. If cache misses, fetches from API and caches the result.
        Returns None if both API and Cache fail.
        """
        cache_key = f"weather:{round(lat, 2)}:{round(lon, 2)}"
        
        # 1. Try Cache
        if self.redis:
            try:
                cached_data = await self.redis.get(cache_key)
                if cached_data:
                    parsed_data = json.loads(cached_data)
                    return CachedWeatherForecast(**parsed_data)
            except Exception as e:
                logger.error(f"Redis cache error: {e}")

        # 2. Fetch from API
        try:
            # We want hourly precipitation to sum for 48h, and daily temp max/min
            params = {
                "latitude": lat,
                "longitude": lon,
                "hourly": "precipitation,relative_humidity_2m",
                "daily": "temperature_2m_max,temperature_2m_min",
                "timezone": "auto",
                "forecast_days": 2
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                
                # Calculate total rainfall in next 48 hours
                hourly_precipitation = data.get("hourly", {}).get("precipitation", [])
                total_rainfall = sum(hourly_precipitation[:48]) if hourly_precipitation else 0.0
                
                # Average humidity
                hourly_humidity = data.get("hourly", {}).get("relative_humidity_2m", [])
                avg_humidity = sum(hourly_humidity[:48]) / min(len(hourly_humidity[:48]), 48) if hourly_humidity else None
                
                # Max and Min temp across 2 days
                daily_tmax = data.get("daily", {}).get("temperature_2m_max", [])
                daily_tmin = data.get("daily", {}).get("temperature_2m_min", [])
                
                max_temp = max(daily_tmax) if daily_tmax else None
                min_temp = min(daily_tmin) if daily_tmin else None
                
                forecast = WeatherForecast(
                    latitude=lat,
                    longitude=lon,
                    total_rainfall_48h_mm=total_rainfall,
                    max_temperature_c=max_temp,
                    min_temperature_c=min_temp,
                    average_humidity_percent=avg_humidity
                )
                
                cached_forecast = CachedWeatherForecast(
                    forecast=forecast,
                    source="Open-Meteo",
                    retrieved_at=datetime.utcnow()
                )
                
                # 3. Save to Cache
                if self.redis:
                    try:
                        # Serialize with json
                        await self.redis.setex(
                            cache_key, 
                            self.cache_ttl_seconds, 
                            cached_forecast.model_dump_json()
                        )
                    except Exception as e:
                        logger.error(f"Redis cache set error: {e}")
                        
                return cached_forecast

        except (httpx.RequestError, httpx.HTTPStatusError, ValidationError) as e:
            logger.error(f"Weather API error: {e}")
            return None

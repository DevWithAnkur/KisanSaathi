from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class WeatherForecast(BaseModel):
    latitude: float = Field(..., description="Latitude of the location")
    longitude: float = Field(..., description="Longitude of the location")
    total_rainfall_48h_mm: float = Field(..., description="Total rainfall expected in the next 48 hours in mm")
    max_temperature_c: Optional[float] = Field(None, description="Maximum temperature expected in Celsius")
    min_temperature_c: Optional[float] = Field(None, description="Minimum temperature expected in Celsius")
    average_humidity_percent: Optional[float] = Field(None, description="Average humidity percentage")
    
class CachedWeatherForecast(BaseModel):
    forecast: WeatherForecast
    source: str = Field(..., description="Source of the weather data (e.g., 'Open-Meteo')")
    retrieved_at: datetime = Field(default_factory=datetime.utcnow, description="When the data was retrieved")

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

from src.models.contracts import AgentRequest
from src.models.weather_models import CachedWeatherForecast, WeatherForecast
from src.integrations.weather import WeatherClient
from src.agents.spoilage import SpoilageAgent

@pytest.fixture
def mock_weather_client():
    client = WeatherClient()
    client.get_48h_forecast = AsyncMock()
    return client

@pytest.fixture
def spoilage_agent(mock_weather_client):
    return SpoilageAgent(weather_client=mock_weather_client)

def build_request(text="when will tomato rot", lat=28.7, lon=77.1, crop="tomato", harvest_date_str=None):
    profile = {"latitude": lat, "longitude": lon}
    if crop:
        profile["crop"] = crop
    if harvest_date_str:
        profile["harvest_date"] = harvest_date_str
        
    return AgentRequest(
        farmer_id="+919876543210",
        session_id="session123",
        message_id="msg123",
        language="en",
        query_text=text,
        profile=profile,
        correlation_id="corr123"
    )

@pytest.mark.asyncio
async def test_spoilage_agent_missing_crop(spoilage_agent, mock_weather_client):
    request = build_request(crop=None)
    response = await spoilage_agent.process_request(request)
    
    assert response.safe_fallback is True
    assert "which crop" in response.text.lower()
    mock_weather_client.get_48h_forecast.assert_not_called()

@pytest.mark.asyncio
async def test_spoilage_agent_missing_harvest_date(spoilage_agent, mock_weather_client):
    request = build_request(crop="tomato", harvest_date_str=None)
    response = await spoilage_agent.process_request(request)
    
    assert response.safe_fallback is True
    assert "harvest date" in response.text.lower()
    mock_weather_client.get_48h_forecast.assert_not_called()

@pytest.mark.asyncio
async def test_spoilage_agent_green_alert(spoilage_agent, mock_weather_client):
    # Setup mock for good weather (Temp < 30)
    mock_weather_client.get_48h_forecast.return_value = CachedWeatherForecast(
        forecast=WeatherForecast(
            latitude=28.7, longitude=77.1, total_rainfall_48h_mm=0.0,
            max_temperature_c=25.0, min_temperature_c=15.0, average_humidity_percent=50.0
        ),
        source="Open-Meteo",
        retrieved_at=datetime.utcnow()
    )
    
    # Harvested today, baseline 30 days for potato
    today = datetime.utcnow().strftime("%Y-%m-%d")
    request = build_request(crop="potato", harvest_date_str=today)
    response = await spoilage_agent.process_request(request)
    
    assert "safe to store" in response.text.lower()
    assert response.verification_status == "verified"

@pytest.mark.asyncio
async def test_spoilage_agent_red_alert_weather_heuristic(spoilage_agent, mock_weather_client):
    # Tomato baseline is 7 days.
    # We harvested 4 days ago -> 3 days left.
    # Bad weather (>30C, >70%) -> cuts in half -> 1 day left -> Red Alert (< 3 days).
    
    mock_weather_client.get_48h_forecast.return_value = CachedWeatherForecast(
        forecast=WeatherForecast(
            latitude=28.7, longitude=77.1, total_rainfall_48h_mm=0.0,
            max_temperature_c=35.0, min_temperature_c=28.0, average_humidity_percent=80.0
        ),
        source="Open-Meteo",
        retrieved_at=datetime.utcnow()
    )
    
    four_days_ago = (datetime.utcnow() - timedelta(days=4)).strftime("%Y-%m-%d")
    request = build_request(crop="tomato", harvest_date_str=four_days_ago)
    response = await spoilage_agent.process_request(request)
    
    assert "red alert" in response.text.lower()
    assert "sell within 1 days" in response.text.lower()

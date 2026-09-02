import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from src.models.contracts import AgentRequest
from src.models.weather_models import CachedWeatherForecast, WeatherForecast
from src.integrations.weather import WeatherClient
from src.agents.irrigation import IrrigationAgent

@pytest.fixture
def mock_weather_client():
    client = WeatherClient()
    client.get_48h_forecast = AsyncMock()
    return client

@pytest.fixture
def irrigation_agent(mock_weather_client):
    return IrrigationAgent(weather_client=mock_weather_client)

def build_request(text="irrigate", lat=28.7, lon=77.1):
    return AgentRequest(
        farmer_id="+919876543210",
        session_id="session123",
        message_id="msg123",
        language="en",
        query_text=text,
        profile={"latitude": lat, "longitude": lon},
        correlation_id="corr123"
    )

@pytest.mark.asyncio
async def test_irrigation_agent_skip_irrigation(irrigation_agent, mock_weather_client):
    # Setup mock to return rainy weather
    mock_weather_client.get_48h_forecast.return_value = CachedWeatherForecast(
        forecast=WeatherForecast(
            latitude=28.7, longitude=77.1, total_rainfall_48h_mm=25.0
        ),
        source="Open-Meteo",
        retrieved_at=datetime.utcnow()
    )
    
    request = build_request()
    response = await irrigation_agent.process_request(request)
    
    assert response.intent == "irrigation"
    assert response.agent_name == "IrrigationAgent"
    assert "skip irrigation" in response.text.lower()
    assert response.verification_status == "verified"
    assert response.source_name == "Open-Meteo"

@pytest.mark.asyncio
async def test_irrigation_agent_do_irrigate(irrigation_agent, mock_weather_client):
    # Setup mock to return dry weather
    mock_weather_client.get_48h_forecast.return_value = CachedWeatherForecast(
        forecast=WeatherForecast(
            latitude=28.7, longitude=77.1, total_rainfall_48h_mm=0.0
        ),
        source="Open-Meteo",
        retrieved_at=datetime.utcnow()
    )
    
    request = build_request()
    response = await irrigation_agent.process_request(request)
    
    assert response.intent == "irrigation"
    assert response.agent_name == "IrrigationAgent"
    assert "irrigate your crop" in response.text.lower()
    assert response.verification_status == "verified"

@pytest.mark.asyncio
async def test_irrigation_agent_missing_location(irrigation_agent, mock_weather_client):
    request = build_request(lat=None, lon=None)
    response = await irrigation_agent.process_request(request)
    
    assert response.safe_fallback is True
    assert response.verification_status == "failed"
    assert "update your profile with your location" in response.text.lower()
    mock_weather_client.get_48h_forecast.assert_not_called()

@pytest.mark.asyncio
async def test_irrigation_agent_weather_api_failure(irrigation_agent, mock_weather_client):
    mock_weather_client.get_48h_forecast.return_value = None
    
    request = build_request()
    response = await irrigation_agent.process_request(request)
    
    assert response.safe_fallback is True
    assert response.verification_status == "failed"
    assert "couldn't fetch the weather" in response.text.lower()

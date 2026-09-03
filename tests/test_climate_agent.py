import pytest
from unittest.mock import AsyncMock

from src.models.contracts import AgentRequest, WeatherData, ForecastData
from src.agents.climate import ClimateAgent
from src.integrations.weather import WeatherClient

@pytest.fixture
def mock_weather_client():
    client = AsyncMock(spec=WeatherClient)
    return client

@pytest.fixture
def climate_agent(mock_weather_client):
    return ClimateAgent(weather_client=mock_weather_client)

def build_request(lang="en"):
    return AgentRequest(
        farmer_id="+91111222333",
        session_id="session123",
        message_id="msg123",
        language=lang,
        query_text="climate alert",
        profile={"onboarding_step": "complete", "state": "MH", "district": "Pune"},
        correlation_id="corr123"
    )

@pytest.mark.asyncio
async def test_climate_heatwave(climate_agent, mock_weather_client):
    # Temp 42 > 40 should trigger heatwave
    mock_weather_client.get_48h_forecast.return_value = WeatherData(
        forecast=ForecastData(max_temperature_c=42.0, total_rainfall_48h_mm=10.0),
        source="MOCK"
    )
    
    request = build_request()
    response = await climate_agent.process_request(request)
    
    assert "HEATWAVE WARNING" in response.text
    assert "HEAVY RAIN" not in response.text

@pytest.mark.asyncio
async def test_climate_heavy_rain(climate_agent, mock_weather_client):
    # Rain 60 > 50 should trigger heavy rain
    mock_weather_client.get_48h_forecast.return_value = WeatherData(
        forecast=ForecastData(max_temperature_c=35.0, total_rainfall_48h_mm=60.0),
        source="MOCK"
    )
    
    request = build_request()
    response = await climate_agent.process_request(request)
    
    assert "HEATWAVE WARNING" not in response.text
    assert "HEAVY RAIN WARNING" in response.text

@pytest.mark.asyncio
async def test_climate_all_clear(climate_agent, mock_weather_client):
    # Normal conditions
    mock_weather_client.get_48h_forecast.return_value = WeatherData(
        forecast=ForecastData(max_temperature_c=35.0, total_rainfall_48h_mm=10.0),
        source="MOCK"
    )
    
    request = build_request()
    response = await climate_agent.process_request(request)
    
    assert "no extreme climate alerts" in response.text.lower()

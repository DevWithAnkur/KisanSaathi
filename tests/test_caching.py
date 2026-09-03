import pytest
from unittest.mock import AsyncMock, patch

from src.models.contracts import AgentRequest, AgentResponse
from src.agents.router import IntentRouter
from src.agents.spoilage import SpoilageAgent

@pytest.fixture
def mock_spoilage_agent():
    agent = AsyncMock(spec=SpoilageAgent)
    return agent

@pytest.fixture
def intent_router(mock_spoilage_agent):
    router = IntentRouter(spoilage_agent=mock_spoilage_agent)
    return router

def build_request(intent="spoilage"):
    return AgentRequest(
        farmer_id="+91111222333",
        session_id="session123",
        message_id="msg123",
        language="en",
        query_text="will my tomatoes rot",
        profile={"onboarding_step": "complete", "state": "MH", "district": "Pune", "crop": "tomato", "harvest_date": "2023-01-01"},
        correlation_id="corr123"
    )

@pytest.mark.asyncio
@patch("src.agents.router.cache")
async def test_successful_response_is_cached(mock_cache, intent_router, mock_spoilage_agent):
    # Setup successful agent response
    mock_spoilage_agent.process_request.return_value = AgentResponse(
        text="Safe to store.", agent_name="Spoilage", intent="spoilage", verification_status="verified"
    )
    request = build_request()
    
    # Process
    # We pass None for db so it bypasses the real db logic in test
    response = await intent_router.process_request("spoilage", request, db=None)
    
    # Verify cache was SET
    mock_cache.set_last_advisory.assert_called_once_with("+91111222333", "spoilage", "Safe to store.")
    assert response.text == "Safe to store."

@pytest.mark.asyncio
@patch("src.agents.router.cache")
async def test_failed_agent_falls_back_to_cache(mock_cache, intent_router, mock_spoilage_agent):
    # Setup failed agent response (e.g. weather API down)
    mock_spoilage_agent.process_request.return_value = AgentResponse(
        text="Weather API is down.", agent_name="Spoilage", intent="spoilage", verification_status="failed", safe_fallback=True
    )
    
    # Setup cache to return old data
    mock_cache.get_last_advisory.return_value = "Safe to store (from yesterday)."
    
    request = build_request()
    response = await intent_router.process_request("spoilage", request, db=None)
    
    # Verify cache was NOT set
    mock_cache.set_last_advisory.assert_not_called()
    
    # Verify cache was GET
    mock_cache.get_last_advisory.assert_called_once_with("+91111222333", "spoilage")
    
    # Verify offline fallback response
    assert "(Offline Fallback)" in response.text
    assert "Safe to store (from yesterday)." in response.text

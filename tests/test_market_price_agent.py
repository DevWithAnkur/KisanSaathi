import pytest
from datetime import datetime
from unittest.mock import AsyncMock

from src.models.contracts import AgentRequest
from src.models.market_models import MarketPrice
from src.integrations.market import MarketClient
from src.agents.market_price import MarketPriceAgent

@pytest.fixture
def mock_market_client():
    client = MarketClient()
    client.get_mandi_price = AsyncMock()
    return client

@pytest.fixture
def market_price_agent(mock_market_client):
    return MarketPriceAgent(market_client=mock_market_client)

def build_request(text="what is the price of wheat", crop="wheat", state="Maharashtra", district="Pune"):
    profile = {}
    if crop:
        profile["crop"] = crop
    if state:
        profile["state"] = state
    if district:
        profile["district"] = district
        
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
async def test_market_price_agent_missing_crop(market_price_agent):
    request = build_request(crop=None)
    response = await market_price_agent.process_request(request)
    
    assert response.safe_fallback is True
    assert "which crop" in response.text.lower()

@pytest.mark.asyncio
async def test_market_price_agent_missing_location(market_price_agent):
    request = build_request(district=None)
    response = await market_price_agent.process_request(request)
    
    assert response.safe_fallback is True
    assert "state and district" in response.text.lower()

@pytest.mark.asyncio
async def test_market_price_agent_no_offered_price(market_price_agent, mock_market_client):
    mock_market_client.get_mandi_price.return_value = MarketPrice(
        crop="wheat", state="Maharashtra", district="Pune",
        mandi_price_inr_per_qtl=2300.0, msp_inr_per_qtl=2275.0,
        source="Agmarknet", retrieved_at=datetime.utcnow()
    )
    
    request = build_request(text="tell me wheat price")
    response = await market_price_agent.process_request(request)
    
    assert response.safe_fallback is False
    assert "2300" in response.text
    assert "msp" in response.text.lower()

@pytest.mark.asyncio
async def test_market_price_agent_low_offered_price(market_price_agent, mock_market_client):
    mock_market_client.get_mandi_price.return_value = MarketPrice(
        crop="wheat", state="Maharashtra", district="Pune",
        mandi_price_inr_per_qtl=2300.0, msp_inr_per_qtl=2275.0,
        source="Agmarknet", retrieved_at=datetime.utcnow()
    )
    
    request = build_request(text="they are offering 2000 per quintal")
    response = await market_price_agent.process_request(request)
    
    assert response.safe_fallback is False
    assert "warning" in response.text.lower()
    assert "lower" in response.text.lower()
    assert "2000" in response.text

@pytest.mark.asyncio
async def test_market_price_agent_fair_offered_price(market_price_agent, mock_market_client):
    mock_market_client.get_mandi_price.return_value = MarketPrice(
        crop="wheat", state="Maharashtra", district="Pune",
        mandi_price_inr_per_qtl=2300.0, msp_inr_per_qtl=2275.0,
        source="Agmarknet", retrieved_at=datetime.utcnow()
    )
    
    request = build_request(text="they are offering 2400 per quintal")
    response = await market_price_agent.process_request(request)
    
    assert response.safe_fallback is False
    assert "good news" in response.text.lower()
    assert "fair" in response.text.lower()
    assert "2400" in response.text

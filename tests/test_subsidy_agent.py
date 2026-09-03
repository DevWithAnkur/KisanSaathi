import pytest
from datetime import datetime

from src.models.contracts import AgentRequest
from src.agents.subsidy import SubsidyAgent

@pytest.fixture
def subsidy_agent():
    return SubsidyAgent()

def build_request(text="schemes for me", state="Maharashtra", crop="wheat", land_size=1.5, category="small"):
    profile = {}
    if state is not None:
        profile["state"] = state
    if crop is not None:
        profile["crop"] = crop
    if land_size is not None:
        profile["land_size_ha"] = land_size
    if category is not None:
        profile["category"] = category
        
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
async def test_subsidy_agent_missing_state(subsidy_agent):
    request = build_request(state=None)
    response = await subsidy_agent.process_request(request)
    
    assert response.safe_fallback is True
    assert "what state" in response.text.lower()
    
@pytest.mark.asyncio
async def test_subsidy_agent_missing_land_size(subsidy_agent):
    request = build_request(land_size=None)
    response = await subsidy_agent.process_request(request)
    
    assert response.safe_fallback is True
    assert "how many hectares" in response.text.lower()

@pytest.mark.asyncio
async def test_subsidy_agent_eligible_pm_kisan(subsidy_agent):
    request = build_request() # Maharashtra, wheat, 1.5, small
    response = await subsidy_agent.process_request(request)
    
    assert response.safe_fallback is False
    assert response.verification_status == "verified"
    assert "pm-kisan" in response.text.lower()
    assert "pmkisan.gov.in" in response.source_name.lower()

@pytest.mark.asyncio
async def test_subsidy_agent_ineligible_large_farmer(subsidy_agent):
    # PM-KISAN in our mock db is up to 2.0 ha, and small/marginal
    request = build_request(land_size=5.0, category="large")
    response = await subsidy_agent.process_request(request)
    
    assert response.safe_fallback is False
    assert "no schemes matching" in response.text.lower() or "pmfby" in response.text.lower()
    
    # Actually PMFBY is available to 'all' and no max land size
    if "pmfby" in response.text.lower():
        assert "pmfby.gov.in" in response.source_name.lower()

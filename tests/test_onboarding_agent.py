import pytest
from unittest.mock import AsyncMock

from src.models.contracts import AgentRequest
from src.agents.onboarding import OnboardingAgent
from src.models.profile_db import FarmerProfileDB

@pytest.fixture
def onboarding_agent():
    return OnboardingAgent()

@pytest.fixture
def mock_db():
    db = AsyncMock()
    return db

def build_request(text="yes"):
    return AgentRequest(
        farmer_id="+919876543210",
        session_id="session123",
        message_id="msg123",
        language="en",
        query_text=text,
        profile={},
        correlation_id="corr123"
    )

@pytest.mark.asyncio
async def test_onboarding_consent_yes(onboarding_agent, mock_db):
    profile = FarmerProfileDB(phone_number="123", onboarding_step="consent")
    request = build_request("Yes I agree")
    response = await onboarding_agent.process_request(request, mock_db, profile)
    
    assert profile.consent_given is True
    assert profile.onboarding_step == "location"
    assert mock_db.commit.called
    assert "state and district" in response.text.lower()

@pytest.mark.asyncio
async def test_onboarding_consent_no(onboarding_agent, mock_db):
    profile = FarmerProfileDB(phone_number="123", onboarding_step="consent")
    request = build_request("No")
    response = await onboarding_agent.process_request(request, mock_db, profile)
    
    assert profile.consent_given is False
    assert profile.onboarding_step == "consent" # Stays on consent
    assert not mock_db.commit.called
    assert "respect your privacy" in response.text.lower()

@pytest.mark.asyncio
async def test_onboarding_location(onboarding_agent, mock_db):
    profile = FarmerProfileDB(phone_number="123", onboarding_step="location")
    request = build_request("Maharashtra, Pune")
    response = await onboarding_agent.process_request(request, mock_db, profile)
    
    assert profile.state == "Maharashtra"
    assert profile.district == "Pune"
    assert profile.onboarding_step == "crop"
    assert mock_db.commit.called
    assert "primary crop" in response.text.lower()

@pytest.mark.asyncio
async def test_onboarding_crop(onboarding_agent, mock_db):
    profile = FarmerProfileDB(phone_number="123", onboarding_step="crop")
    request = build_request("wheat")
    response = await onboarding_agent.process_request(request, mock_db, profile)
    
    assert profile.crop == "wheat"
    assert profile.onboarding_step == "details"
    assert mock_db.commit.called
    assert "hectares of land" in response.text.lower() or "land size" in response.text.lower()

@pytest.mark.asyncio
async def test_onboarding_details(onboarding_agent, mock_db):
    profile = FarmerProfileDB(phone_number="123", onboarding_step="details")
    request = build_request("2.5 hectares, small")
    response = await onboarding_agent.process_request(request, mock_db, profile)
    
    assert profile.land_size_ha == "2.5"
    assert profile.category == "small"
    assert profile.onboarding_step == "language"
    assert mock_db.commit.called
    assert "language" in response.text.lower()

@pytest.mark.asyncio
async def test_onboarding_language(onboarding_agent, mock_db):
    profile = FarmerProfileDB(phone_number="123", onboarding_step="language")
    request = build_request("hi")
    response = await onboarding_agent.process_request(request, mock_db, profile)
    
    assert profile.language == "hi"
    assert profile.onboarding_step == "pump"
    assert mock_db.commit.called
    # Response will be in Hindi, check for pump-related content
    assert "पंप" in response.text or "pump" in response.text.lower()

@pytest.mark.asyncio
async def test_onboarding_pump_skip(onboarding_agent, mock_db):
    profile = FarmerProfileDB(phone_number="123", onboarding_step="pump")
    request = build_request("skip")
    response = await onboarding_agent.process_request(request, mock_db, profile)
    
    assert profile.onboarding_step == "complete"
    assert mock_db.commit.called
    assert "profile is set up" in response.text.lower()

@pytest.mark.asyncio
async def test_onboarding_pump_diesel(onboarding_agent, mock_db):
    profile = FarmerProfileDB(phone_number="123", onboarding_step="pump")
    request = build_request("diesel, 5")
    response = await onboarding_agent.process_request(request, mock_db, profile)
    
    assert profile.pump_type == "diesel"
    assert profile.motor_hp == 5.0
    assert profile.onboarding_step == "complete"
    assert mock_db.commit.called
    assert "profile is set up" in response.text.lower()

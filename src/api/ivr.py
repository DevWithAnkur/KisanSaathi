from fastapi import APIRouter, Request, Depends
from fastapi.responses import Response
import logging
import uuid

# In a real app, these would be properly injected dependencies
from src.agents.router import IntentRouter
from src.core.database import get_db
from src.models.contracts import AgentRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ivr", tags=["IVR"])

# Placeholder for the global router instance which would normally be injected
intent_router = IntentRouter()

def generate_twiml(text: str, gather: bool = False) -> str:
    """Helper to generate basic Twilio TwiML XML."""
    twiml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Say language="en-IN">{text}</Say>'
    if gather:
        # Prompt for voice input and send result to /ivr/process
        twiml += '<Gather input="speech" action="/ivr/process" timeout="5"></Gather>'
    twiml += '</Response>'
    return twiml

@router.post("/incoming")
async def ivr_incoming(request: Request):
    """
    Initial webhook hit by Twilio when a farmer calls the phone number.
    """
    form_data = await request.form()
    caller_id = form_data.get("From", "Unknown")
    logger.info(f"Incoming IVR call from {caller_id}")
    
    welcome_text = "Welcome to Kisan Saathi. Please tell me your question after the beep."
    return Response(content=generate_twiml(welcome_text, gather=True), media_type="application/xml")

@router.post("/process")
async def ivr_process(request: Request, db=Depends(get_db)):
    """
    Processes the transcribed voice from the Twilio <Gather> verb.
    """
    form_data = await request.form()
    caller_id = form_data.get("From", "Unknown")
    speech_result = form_data.get("SpeechResult", "")
    
    logger.info(f"IVR received speech from {caller_id}: {speech_result}")
    
    if not speech_result:
        return Response(content=generate_twiml("I didn't catch that. Please try calling again later."), media_type="application/xml")
        
    # Route through the same pipeline as WhatsApp
    intent = intent_router.classify_intent(speech_result)
    
    agent_request = AgentRequest(
        farmer_id=caller_id,
        session_id=caller_id,
        message_id=str(uuid.uuid4()),
        language="en",
        query_text=speech_result,
        correlation_id=str(uuid.uuid4())
    )
    
    # Process request
    # Note: Using mock empty router here because dependencies are not wired globally.
    response = await intent_router.process_request(intent, agent_request, db)
    
    return Response(content=generate_twiml(response.text, gather=False), media_type="application/xml")

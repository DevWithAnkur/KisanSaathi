from fastapi import APIRouter, Request, HTTPException, Depends, Header
from fastapi.responses import PlainTextResponse
from typing import Any, Dict
import json
import logging

from src.core.config import settings
from src.core.security import verify_whatsapp_signature, sanitize_input, contains_profanity
from src.core.rate_limit import rate_limiter
from src.core.session import session_manager
from src.agents.router import intent_router
from src.models.contracts import AgentRequest
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["Webhook"])

@router.get("")
async def verify_webhook(
    "hub.mode": str = None, 
    "hub.challenge": str = None, 
    "hub.verify_token": str = None
):
    """
    Endpoint for Meta to verify the webhook URL.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return PlainTextResponse(content=hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")

@router.post("")
async def receive_message(
    request: Request,
    x_hub_signature_256: str = Header(None),
    _: bool = Depends(rate_limiter.check_rate_limit)
):
    """
    Endpoint to receive incoming WhatsApp messages.
    """
    body_bytes = await request.body()
    
    # 1. Verify Signature
    if not x_hub_signature_256 or not verify_whatsapp_signature(body_bytes, x_hub_signature_256, settings.whatsapp_api_token):
        logger.warning("Invalid webhook signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    # 2. Parse Body
    try:
        data = json.loads(body_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # 3. Extract Message Details (simplified for MVP)
    # A real implementation would deeply inspect the Meta webhook payload structure
    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        
        if "messages" not in value:
            return {"status": "ok", "detail": "No messages found in payload"}
            
        message = value["messages"][0]
        farmer_id = message["from"]
        msg_id = message["id"]
        
    except (KeyError, IndexError) as e:
        logger.error(f"Error parsing webhook payload: {e}")
        return {"status": "ok", "detail": "Unrecognized payload structure"}

    # 4. Extract text or process voice
    query_text = ""
    if message["type"] == "text":
        query_text = message["text"]["body"]
    elif message["type"] == "audio":
        # Placeholder for voice validation and STT
        # stt_result = stt_client.process_audio(audio_data, mime_type)
        # if stt_result.confidence < 0.7: return ask_to_repeat()
        query_text = "mock transcribed audio"
    else:
        return {"status": "ok", "detail": "Unsupported message type"}

    # 5. Sanitize & Profanity Check
    sanitized_text = sanitize_input(query_text)
    if contains_profanity(sanitized_text):
        logger.warning(f"Profanity detected from {farmer_id}")
        # In a real app, send a polite refusal via WhatsApp API
        return {"status": "ok", "detail": "Profanity detected. Message rejected."}

    # 6. Classify Intent
    intent = intent_router.classify_intent(sanitized_text)
    
    # 7. Handle Fallbacks
    if intent == "unclassified":
        failures = session_manager.increment_failure_count(farmer_id)
        if failures >= 2:
            menu = intent_router.get_fallback_menu("en")
            session_manager.reset_failure_count(farmer_id)
            # In real app, send menu via WhatsApp API
            logger.info(f"Sending fallback menu to {farmer_id}: {menu}")
            return {"status": "ok", "intent": "fallback_menu"}
    else:
        session_manager.reset_failure_count(farmer_id)

    # 8. Create Agent Request
    agent_request = AgentRequest(
        farmer_id=farmer_id,
        session_id=farmer_id, # Simplified session ID
        message_id=msg_id,
        language="en", # Hardcoded for now
        query_text=sanitized_text,
        correlation_id=str(uuid.uuid4())
    )

    # 9. Route to specific Agent (Placeholder)
    # response = dispatch_to_agent(intent, agent_request)

    logger.info(f"Successfully processed message {msg_id}, intent: {intent}")
    return {"status": "ok", "intent": intent}

from fastapi import APIRouter, Request, HTTPException, Depends, Header, Query
from fastapi.responses import PlainTextResponse
import json
import logging
import re
import time

from src.core.config import settings
from src.core.security import (
    verify_whatsapp_signature,
    sanitize_input,
    contains_profanity,
)
from src.core.rate_limit import get_rate_limiter
from src.core.session import session_manager
from src.agents.router import intent_router
from src.models.contracts import AgentRequest
from src.integrations import stt_client, tts_client, whatsapp_client, TranslationClient
import uuid
import redis.asyncio as redis
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["Webhook"])

# Initialize translation client
translation_client = TranslationClient()

# Confidence threshold for STT (FR-28)
STT_CONFIDENCE_THRESHOLD = 0.7

# Devanagari script range for Hindi detection
DEVANAGARI_PATTERN = re.compile(r"[\u0900-\u097F]")


def detect_language(text: str, profile_language: Optional[str] = None) -> str:
    """
    Detect language from text content.
    Priority: 1) Profile language preference, 2) Script detection (Devanagari = Hindi), 3) Default to English
    """
    # Use profile language if available
    if profile_language and profile_language in ["hi", "mr", "en"]:
        return profile_language

    # Detect Devanagari script (Hindi, Marathi, etc.)
    if DEVANAGARI_PATTERN.search(text):
        return "hi"  # Default to Hindi for Devanagari

    # Default to English
    return "en"


# Idempotency key management (duplicate message detection)
_idempotency_redis = None
_idempotency_redis_available = False
_idempotency_memory: dict[str, float] = (
    {}
)  # fallback: {msg_id: expiry_timestamp}  # type: ignore
IDEMPOTENCY_TTL = 86400  # 24 hours


async def _get_idempotency_redis():
    global _idempotency_redis, _idempotency_redis_available
    if _idempotency_redis is None:
        try:
            _idempotency_redis = redis.from_url(
                settings.redis_url, decode_responses=True
            )
            await _idempotency_redis.ping()
            _idempotency_redis_available = True
            logger.info("Redis connection established for idempotency keys")
        except Exception as e:
            logger.warning(f"Redis unavailable for idempotency, using in-memory: {e}")
            _idempotency_redis_available = False
            _idempotency_redis = None
    return _idempotency_redis


def _cleanup_idempotency_memory():
    """Remove expired entries from memory store."""
    now = time.time()
    expired = [k for k, v in _idempotency_memory.items() if v < now]
    for k in expired:
        del _idempotency_memory[k]


async def check_and_store_idempotency_key(msg_id: str) -> bool:
    """
    Check if message ID has been processed before.
    Returns True if this is a new message (not a duplicate), False if duplicate.
    """
    key = f"idempotency:{msg_id}"
    client = await _get_idempotency_redis()
    now = time.time()
    expiry = now + IDEMPOTENCY_TTL

    if _idempotency_redis_available and client:
        try:
            # Use SET NX (set if not exists) with expiry
            result = await client.set(key, str(expiry), nx=True, ex=IDEMPOTENCY_TTL)
            if result:
                return True  # New message
            else:
                # Key exists, check if it's expired
                existing = await client.get(key)
                if existing and float(existing) < now:
                    # Expired, try to overwrite
                    result = await client.set(
                        key, str(expiry), xx=True, ex=IDEMPOTENCY_TTL
                    )
                    return result is not None
                return False  # Duplicate
        except Exception as e:
            logger.warning(
                f"Redis error during idempotency check, falling back to memory: {e}"
            )
            # Fall through to memory

    # Fallback: in-memory store
    _cleanup_idempotency_memory()
    if key in _idempotency_memory:
        if _idempotency_memory[key] < now:
            # Expired, allow
            _idempotency_memory[key] = expiry
            return True
        return False  # Duplicate

    _idempotency_memory[key] = expiry
    return True  # New message


@router.get("")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
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
    rate_limiter=Depends(get_rate_limiter),
):
    """
    Endpoint to receive incoming WhatsApp messages.
    """
    body_bytes = await request.body()

    # 1. Verify Signature
    if not x_hub_signature_256 or not verify_whatsapp_signature(
        body_bytes, x_hub_signature_256, settings.whatsapp_api_token
    ):
        logger.warning("Invalid webhook signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    # 2. Parse Body
    try:
        data = json.loads(body_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # 3. Extract Message Details (simplified for MVP)
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

    # 4. Idempotency Check (duplicate message detection)
    is_new_message = await check_and_store_idempotency_key(msg_id)
    if not is_new_message:
        logger.info(f"Duplicate message ignored: {msg_id}")
        return {"status": "ok", "detail": "Duplicate message ignored"}

    # 5. Rate Limit Check (after farmer_id extraction)
    client_ip = request.client.host if request.client else "unknown"
    await rate_limiter.check_rate_limit(farmer_id, client_ip)

    # 5. Extract text or process voice
    query_text = ""
    detected_language = "en"  # Default
    profile_language = None

    # Try to get profile language from DB for text messages
    if message["type"] == "text":
        from src.core.database import get_db

        db = None
        async for session in get_db():
            db = session
            break
        if db:
            try:
                from sqlalchemy.future import select
                from src.models.profile_db import FarmerProfileDB

                result = await db.execute(
                    select(FarmerProfileDB).filter(
                        FarmerProfileDB.phone_number == farmer_id
                    )
                )
                profile = result.scalars().first()
                if profile and profile.onboarding_step == "complete":
                    # We don't store language in profile yet, but we could add it
                    pass
            except Exception:
                pass  # Ignore DB errors for language detection

        query_text = message["text"]["body"]
        detected_language = detect_language(query_text, profile_language)

    elif message["type"] == "audio":
        # Process voice note
        audio_info = message.get("audio", {})
        mime_type = audio_info.get("mime_type", "audio/ogg")
        file_size = audio_info.get("file_size", 0)
        duration_secs = audio_info.get("duration", 0)
        media_id = audio_info.get("id")

        # Validate voice note metadata
        if not whatsapp_client.validate_voice_note(mime_type, file_size, duration_secs):
            await whatsapp_client.send_text_message(
                farmer_id,
                "Sorry, I couldn't process that voice note. Please try again with a shorter message.",
            )
            return {"status": "ok", "detail": "Voice note validation failed"}

        # Download audio
        if not media_id:
            await whatsapp_client.send_text_message(
                farmer_id,
                "Sorry, I couldn't retrieve the voice note. Please try again.",
            )
            return {"status": "ok", "detail": "No media ID"}

        audio_data, actual_mime_type = await whatsapp_client.download_media(
            media_id, farmer_id
        )
        if not audio_data:
            await whatsapp_client.send_text_message(
                farmer_id,
                "Sorry, I couldn't download the voice note. Please try again.",
            )
            return {"status": "ok", "detail": "Audio download failed"}

        # Get S3 key from download_media (if uploaded)
        media_info = message.get("audio", {})
        s3_key = media_info.get("s3_key")

        # Transcribe with STT
        try:
            stt_result = await stt_client.process_audio(
                audio_data, actual_mime_type or mime_type
            )
            query_text = stt_result.text
            detected_language = stt_result.language

            # Check confidence threshold (FR-28)
            if stt_result.confidence < STT_CONFIDENCE_THRESHOLD:
                await whatsapp_client.send_text_message(
                    farmer_id,
                    "Sorry, I didn't catch that clearly. Could you say it again?",
                )
                # Mark as failed for retry (24h retention)
                if s3_key:
                    await whatsapp_client.mark_voice_failed(farmer_id, s3_key)
                return {"status": "ok", "intent": "low_confidence_stt"}

            # Mark as processed (will be auto-deleted by lifecycle policy)
            if s3_key:
                await whatsapp_client.mark_voice_processed(farmer_id, s3_key)

        except Exception as e:
            logger.error(f"STT processing failed: {e}")
            # Mark as failed for retry (24h retention)
            if s3_key:
                await whatsapp_client.mark_voice_failed(farmer_id, s3_key)
            await whatsapp_client.send_text_message(
                farmer_id,
                "Sorry, I had trouble understanding your voice note. Please try again.",
            )
            return {"status": "ok", "detail": "STT failed"}

    else:
        return {"status": "ok", "detail": "Unsupported message type"}

    # 6. Sanitize & Profanity Check
    sanitized_text = sanitize_input(query_text)
    if contains_profanity(sanitized_text):
        logger.warning(f"Profanity detected from {farmer_id}")
        await whatsapp_client.send_text_message(
            farmer_id, "Please keep your questions respectful. How can I help you?"
        )
        return {"status": "ok", "detail": "Profanity detected. Message rejected."}

    # 7. Classify Intent
    intent = intent_router.classify_intent(sanitized_text)

    # 8. Handle Fallbacks
    if intent == "unclassified":
        failures = session_manager.increment_failure_count(farmer_id)
        if failures >= 2:  # type: ignore
            menu = intent_router.get_fallback_menu(detected_language)
            session_manager.reset_failure_count(farmer_id)
            # Send fallback menu via WhatsApp
            await whatsapp_client.send_text_message(farmer_id, menu)
            return {"status": "ok", "intent": "fallback_menu"}
    else:
        session_manager.reset_failure_count(farmer_id)

    # 9. Create Agent Request
    agent_request = AgentRequest(
        farmer_id=farmer_id,
        session_id=farmer_id,
        message_id=msg_id,
        language=detected_language,
        query_text=sanitized_text,
        correlation_id=str(uuid.uuid4()),
    )

    # 10. Route to Agent & Get Response
    from src.core.database import get_db

    db = None
    async for session in get_db():
        db = session
        break  # Get first (and only) session

    response = await intent_router.process_request(intent, agent_request, db)

    # 11. Translate response to farmer's language
    if response.text and detected_language != "en":
        try:
            translated_text = await translation_client.translate(
                response.text, detected_language
            )
            response.text = translated_text
        except Exception as e:
            logger.warning(f"Translation failed, using English: {e}")

    # 12. Send response via WhatsApp (text + audio)
    try:
        # Send text message
        await whatsapp_client.send_text_message(farmer_id, response.text)

        # Generate and send audio response
        tts_result = await tts_client.synthesize(response.text, detected_language)
        await whatsapp_client.send_audio_message(
            farmer_id, tts_result.audio_data, tts_result.mime_type
        )

    except Exception as e:
        logger.error(f"Failed to send WhatsApp response: {e}")
        # At least log the response for debugging
        logger.info(f"Response that failed to send: {response.text}")

    logger.info(
        f"Successfully processed message {msg_id}, intent: {intent}, lang: {detected_language}"
    )
    return {"status": "ok", "intent": intent, "language": detected_language}

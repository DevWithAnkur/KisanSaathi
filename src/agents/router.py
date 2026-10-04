import logging
import inspect
from typing import Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

from ..core.cache import cache
from ..models.contracts import AgentRequest, AgentResponse
from ..models.profile_db import FarmerProfileDB
from .irrigation import IrrigationAgent
from .spoilage import SpoilageAgent
from .subsidy import SubsidyAgent
from .market_price import MarketPriceAgent
from .onboarding import OnboardingAgent
from .climate import ClimateAgent

logger = logging.getLogger(__name__)

class IntentRouter:
    def __init__(self, irrigation_agent: Optional[IrrigationAgent] = None, spoilage_agent: Optional[SpoilageAgent] = None, subsidy_agent: Optional[SubsidyAgent] = None, market_price_agent: Optional[MarketPriceAgent] = None, onboarding_agent: Optional[OnboardingAgent] = None, climate_agent: Optional[ClimateAgent] = None):
        self.supported_intents = ["irrigation", "spoilage", "climate", "subsidy", "market_price", "delete_profile"]
        self.irrigation_agent = irrigation_agent
        self.spoilage_agent = spoilage_agent
        self.subsidy_agent = subsidy_agent
        self.market_price_agent = market_price_agent
        self.onboarding_agent = onboarding_agent
        self.climate_agent = climate_agent
        
        # Simple keyword matching for MVP routing
        self.keywords = {
            "irrigation": ["water", "irrigate", "pump", "dry", "rain"],
            "spoilage": ["spoil", "rot", "store", "harvest", "shelf"],
            "climate": ["weather", "hot", "cold", "frost", "alert"],
            "subsidy": ["scheme", "pm-kisan", "money", "apply", "benefit"],
            "market_price": ["price", "sell", "mandi", "rate", "offer"],
            "delete_profile": ["delete my data", "delete profile", "remove my data", "erase my data", "forget me", "gdpr", "data deletion", "delete account"]
        }

    def classify_intent(self, text: str) -> str:
        """
        Classifies the intent based on a sanitized text query.
        Returns the intent name or 'unclassified'
        """
        text = text.lower()
        
        # Naive keyword matching logic
        for intent, words in self.keywords.items():
            if any(word in text for word in words):
                return intent
                
        return "unclassified"

    def get_fallback_menu(self, language: str) -> str:
        """
        Returns the 5-option spoken menu for unclassified intents.
        """
        # In reality, this would fetch from a localized string bundle
        return (
            "I couldn't understand that. You can ask me about:\n"
            "1. Irrigation advice\n"
            "2. Spoilage risk\n"
            "3. Climate alerts\n"
            "4. Subsidy schemes\n"
            "5. Market prices"
        )

    async def process_request(self, intent: str, request: AgentRequest, db: AsyncSession = None) -> AgentResponse:
        """
        Routes the request to the appropriate agent after handling onboarding.
        """
        profile = None
        if db:
            try:
                result = await db.execute(select(FarmerProfileDB).filter(FarmerProfileDB.phone_number == request.farmer_id))
                profile = result.scalars().first()
                
                if not profile:
                    profile = FarmerProfileDB(phone_number=request.farmer_id)
                    db.add(profile)
                    await db.commit()
                    await db.refresh(profile)
                    
                if profile.onboarding_step != "complete" and self.onboarding_agent:
                    return await self.onboarding_agent.process_request(request, db, profile)
                    
                # If onboarding is complete, populate request profile with decrypted data
                if profile.onboarding_step == "complete":
                    request.profile = {
                        "state": profile.state,
                        "district": profile.district,
                        "crop": profile.crop,
                        "land_size_ha": float(profile.land_size_ha) if profile.land_size_ha else None,
                        "category": profile.category,
                        "harvest_date": profile.harvest_date,
                        "pump_type": profile.pump_type,
                        "motor_hp": float(profile.motor_hp) if profile.motor_hp else None
                    }
            except SQLAlchemyError as e:
                logger.warning(f"Database unavailable, proceeding without profile: {e}")
                # Proceed without profile data
                pass
        
        # Standard agent routing
        response = None
        try:
            if intent == "irrigation" and self.irrigation_agent:
                response = await self.irrigation_agent.process_request(request)
                
            elif intent == "spoilage" and self.spoilage_agent:
                response = await self.spoilage_agent.process_request(request)
                
            elif intent == "subsidy" and self.subsidy_agent:
                response = await self.subsidy_agent.process_request(request)
                
            elif intent == "market_price" and self.market_price_agent:
                response = await self.market_price_agent.process_request(request)
                
            elif intent == "climate" and self.climate_agent:
                response = await self.climate_agent.process_request(request)
                
            elif intent == "delete_profile" and self.onboarding_agent:
                response = await self.onboarding_agent.handle_deletion_request(request, db)
                
        except Exception as e:
            logger.error(f"Agent processing failed for {intent}: {e}")

        # Caching logic
        if response and not getattr(response, 'safe_fallback', False) and getattr(response, 'verification_status', None) != "failed":
            # Successful response, cache it with source metadata
            cache_result = cache.set_last_advisory(
                request.farmer_id, 
                intent, 
                response.text,
                response.source_name,
                response.source_timestamp
            )
            if inspect.isawaitable(cache_result):
                await cache_result
            return response
            
        # If response failed or exception occurred, try to fallback to cache
        cached_advisory = cache.get_last_advisory(request.farmer_id, intent)
        if inspect.isawaitable(cached_advisory):
            cached_advisory = await cached_advisory
            
        if cached_advisory:
            # Check for conflicting data (FR-31)
            conflict_msg = None
            if response and hasattr(response, 'text') and response.text:
                conflict_msg = await cache.compare_and_flag_conflict(
                    request.farmer_id, intent, response.text,
                    response.source_name or "unknown",
                    response.source_timestamp or datetime.utcnow()
                )
            
            cached_text = cached_advisory.text
            if conflict_msg:
                # Surface the conflict to the user
                cached_text = f"{conflict_msg} {cached_text}"
            
            return AgentResponse(
                text=f"(Offline Fallback) {cached_text}",
                agent_name="CacheFallback",
                intent=intent,
                source_name=cached_advisory.source_name,
                source_timestamp=cached_advisory.source_timestamp,
                safe_fallback=True
            )
            
        if response:
            return response

        # Fallback for unimplemented agents or unclassified
        text = self.get_fallback_menu(request.language)
        return AgentResponse(
            text=text,
            agent_name="IntentRouter",
            intent=intent,
            safe_fallback=True
        )

intent_router = IntentRouter()

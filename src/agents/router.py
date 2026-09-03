import logging
from typing import Optional

from ..models.contracts import AgentRequest, AgentResponse
from .irrigation import IrrigationAgent
from .spoilage import SpoilageAgent
from .subsidy import SubsidyAgent
from .market_price import MarketPriceAgent

logger = logging.getLogger(__name__)

class IntentRouter:
    def __init__(self, irrigation_agent: Optional[IrrigationAgent] = None, spoilage_agent: Optional[SpoilageAgent] = None, subsidy_agent: Optional[SubsidyAgent] = None, market_price_agent: Optional[MarketPriceAgent] = None):
        self.supported_intents = ["irrigation", "spoilage", "climate", "subsidy", "market_price"]
        self.irrigation_agent = irrigation_agent
        self.spoilage_agent = spoilage_agent
        self.subsidy_agent = subsidy_agent
        self.market_price_agent = market_price_agent
        
        # Simple keyword matching for MVP routing
        self.keywords = {
            "irrigation": ["water", "irrigate", "pump", "dry", "rain"],
            "spoilage": ["spoil", "rot", "store", "harvest", "shelf"],
            "climate": ["weather", "hot", "cold", "frost", "alert"],
            "subsidy": ["scheme", "pm-kisan", "money", "apply", "benefit"],
            "market_price": ["price", "sell", "mandi", "rate", "offer"]
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

    async def route_request(self, request: AgentRequest) -> AgentResponse:
        """
        Routes the request to the appropriate agent based on intent.
        """
        intent = self.classify_intent(request.query_text)
        
        if intent == "irrigation" and self.irrigation_agent:
            return await self.irrigation_agent.process_request(request)
            
        if intent == "spoilage" and self.spoilage_agent:
            return await self.spoilage_agent.process_request(request)
            
        if intent == "subsidy" and self.subsidy_agent:
            return await self.subsidy_agent.process_request(request)
            
        if intent == "market_price" and self.market_price_agent:
            return await self.market_price_agent.process_request(request)
            
        # Fallback for unimplemented agents or unclassified
        text = self.get_fallback_menu(request.language)
        return AgentResponse(
            text=text,
            agent_name="IntentRouter",
            intent=intent,
            safe_fallback=True
        )

# Note: The global instance is commented out because it requires dependencies.
# We will likely inject dependencies in the FastAPI routes.
# intent_router = IntentRouter()

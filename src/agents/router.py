import logging
from typing import Optional

logger = logging.getLogger(__name__)

class IntentRouter:
    def __init__(self):
        self.supported_intents = ["irrigation", "spoilage", "climate", "subsidy", "market_price"]
        
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

intent_router = IntentRouter()

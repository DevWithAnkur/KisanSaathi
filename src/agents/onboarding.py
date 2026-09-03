import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.contracts import AgentRequest, AgentResponse
from ..models.profile_db import FarmerProfileDB

logger = logging.getLogger(__name__)

class OnboardingAgent:
    
    async def process_request(self, request: AgentRequest, db: AsyncSession, profile: FarmerProfileDB) -> AgentResponse:
        """
        State machine for onboarding. 
        """
        step = profile.onboarding_step
        text_lower = request.query_text.lower()
        
        if step == "consent":
            # Check if they just answered the consent question
            if "yes" in text_lower or "हां" in text_lower or "haan" in text_lower:
                profile.consent_given = True
                profile.onboarding_step = "location"
                await db.commit()
                text = "Thank you. To provide accurate weather and market data, which state and district are you from? (e.g., 'Maharashtra, Pune')" if request.language != "hi" else "धन्यवाद। सटीक मौसम और बाजार डेटा प्रदान करने के लिए, आप किस राज्य और जिले से हैं? (उदा., 'महाराष्ट्र, पुणे')"
                return self._build_response(request, text)
            elif "no" in text_lower or "नहीं" in text_lower or "nahi" in text_lower:
                text = "I respect your privacy. Without consent to process your voice and location, I cannot provide advisories. Have a good day." if request.language != "hi" else "मैं आपकी गोपनीयता का सम्मान करता हूँ। आपकी आवाज़ और स्थान को संसाधित करने की सहमति के बिना, मैं सलाह प्रदान नहीं कर सकता।"
                return self._build_response(request, text)
            else:
                # Ask for consent
                text = "Welcome to KisanSaathi! Before we start, I need your consent to temporarily process your voice notes and store your location for agricultural advisories. Do you agree? (Yes/No)" if request.language != "hi" else "किसानसाथी में आपका स्वागत है! शुरू करने से पहले, मुझे आपके वॉयस नोट्स को संसाधित करने और कृषि सलाह के लिए आपके स्थान को संग्रहीत करने के लिए आपकी सहमति की आवश्यकता है। क्या आप सहमत हैं? (हाँ/नहीं)"
                return self._build_response(request, text)
                
        elif step == "location":
            # Extract state and district (very simplified for MVP)
            # e.g., "Maharashtra, Pune"
            parts = request.query_text.split(",")
            if len(parts) >= 2:
                profile.state = parts[0].strip()
                profile.district = parts[1].strip()
                profile.onboarding_step = "crop"
                await db.commit()
                text = "Got it. What is the primary crop you are growing right now?" if request.language != "hi" else "समझ गया। अभी आप मुख्य रूप से कौन सी फसल उगा रहे हैं?"
                return self._build_response(request, text)
            else:
                text = "Please provide both your state and district, separated by a comma. (e.g., 'Maharashtra, Pune')" if request.language != "hi" else "कृपया अपना राज्य और जिला दोनों प्रदान करें, अल्पविराम द्वारा अलग किए गए। (उदा., 'महाराष्ट्र, पुणे')"
                return self._build_response(request, text)
                
        elif step == "crop":
            profile.crop = request.query_text.strip()
            profile.onboarding_step = "details"
            await db.commit()
            text = "Almost done! How many hectares of land do you farm, and are you a small, marginal, or large farmer? (e.g., '2 hectares, small')" if request.language != "hi" else "लगभग पूरा हो गया! आप कितने हेक्टेयर भूमि पर खेती करते हैं, और क्या आप एक छोटे, सीमांत या बड़े किसान हैं? (उदा., '2 हेक्टेयर, छोटे')"
            return self._build_response(request, text)
            
        elif step == "details":
            parts = request.query_text.split(",")
            if len(parts) >= 2:
                # Extract numbers from parts[0]
                import re
                match = re.search(r'\d+(?:\.\d+)?', parts[0])
                if match:
                    profile.land_size_ha = match.group(0)
                profile.category = parts[1].strip()
                profile.onboarding_step = "complete"
                await db.commit()
                text = "Your profile is set up! You can now ask me about irrigation, spoilage risks, subsidies, or market prices." if request.language != "hi" else "आपकी प्रोफ़ाइल सेट हो गई है! अब आप मुझसे सिंचाई, खराब होने के जोखिमों, सब्सिडी या बाजार की कीमतों के बारे में पूछ सकते हैं।"
                return self._build_response(request, text)
            else:
                text = "Please provide your land size and category, separated by a comma. (e.g., '2 hectares, small')" if request.language != "hi" else "कृपया अपनी भूमि का आकार और श्रेणी प्रदान करें, अल्पविराम द्वारा अलग किए गए। (उदा., '2 हेक्टेयर, छोटे')"
                return self._build_response(request, text)
                
        return self._build_response(request, "Onboarding complete.", safe_fallback=True)

    def _build_response(self, request: AgentRequest, text: str, **kwargs) -> AgentResponse:
        return AgentResponse(
            text=text,
            agent_name="OnboardingAgent",
            intent="onboarding",
            response_timestamp=datetime.utcnow(),
            **kwargs
        )

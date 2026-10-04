import logging
import re
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.contracts import AgentRequest, AgentResponse
from ..models.profile_db import FarmerProfileDB

logger = logging.getLogger(__name__)

# Legal Disclaimer (PRD FR-27, Section 14)
LEGAL_DISCLAIMER = (
    "KisanSaathi provides agricultural advisory information for educational purposes only. "
    "The information provided is based on publicly available data sources and automated analysis, "
    "and should not be considered professional agricultural, legal, or financial advice. "
    "KisanSaathi does not guarantee the accuracy, completeness, or timeliness of any information. "
    "Farmers should verify critical decisions with local agricultural extension officers, "
    "certified crop advisors, or relevant government departments before taking action. "
    "KisanSaathi and its operators are not liable for any losses, damages, or adverse outcomes "
    "resulting from the use of this service. By using KisanSaathi, you acknowledge that you "
    "understand this disclaimer and consent to the processing of your voice and location data "
    "as described in our privacy policy."
)

LEGAL_DISCLAIMER_HI = (
    "किसानसाथी केवल शैक्षिक उद्देश्यों के लिए कृषि सलाह जानकारी प्रदान करता है। "
    "प्रदान की गई जानकारी सार्वजनिक रूप से उपलब्ध डेटा स्रोतों और स्वचालित विश्लेषण पर आधारित है, "
    "और इसे पेशेवर कृषि, कानूनी या वित्तीय सलाह नहीं माना जाना चाहिए। "
    "किसानसाथी किसी भी जानकारी की सटीकता, पूर्णता या समयबद्धता की गारंटी नहीं देता है। "
    "किसानों को कोई भी कार्रवाई करने से पहले स्थानीय कृषि विस्तार अधिकारियों, "
    "प्रमाणित फसल सलाहकारों, या संबंधित सरकारी विभागों से महत्वपूर्ण निर्णयों की पुष्टि करनी चाहिए। "
    "किसानसाथी और इसके संचालक इस सेवा के उपयोग से होने वाले किसी भी नुकसान, क्षति, "
    "या प्रतिकूल परिणाम के लिए उत्तरदायी नहीं हैं। किसानसाथी का उपयोग करके, आप स्वीकार करते हैं "
    "कि आप इस अस्वीकरण को समझते हैं और हमारी गोपनीयता नीति के अनुसार "
    "अपनी आवाज और स्थान डेटा के प्रसंस्करण के लिए सहमति देते हैं।"
)


class OnboardingAgent:

    async def process_request(
        self, request: AgentRequest, db: AsyncSession, profile: FarmerProfileDB
    ) -> AgentResponse:
        """
        State machine for onboarding.
        Steps: consent -> location -> crop -> details -> pump (optional) -> complete
        """
        step = profile.onboarding_step
        text_lower = request.query_text.lower()

        if step == "consent":
            # Check if they just answered the consent question
            if "yes" in text_lower or "हां" in text_lower or "haan" in text_lower:
                profile.consent_given = True
                profile.onboarding_step = "location"
                await db.commit()
                text = (
                    "Thank you. To provide accurate weather and market data, which state and district are you from? (e.g., 'Maharashtra, Pune')"
                    if request.language != "hi"
                    else "धन्यवाद। सटीक मौसम और बाजार डेटा प्रदान करने के लिए, आप किस राज्य और जिले से हैं? (उदा., 'महाराष्ट्र, पुणे')"
                )
                return self._build_response(request, text)
            elif "no" in text_lower or "नहीं" in text_lower or "nahi" in text_lower:
                profile.consent_given = False
                text = (
                    "I respect your privacy. Without consent to process your voice and location, I cannot provide advisories. Have a good day."
                    if request.language != "hi"
                    else "मैं आपकी गोपनीयता का सम्मान करता हूँ। आपकी आवाज़ और स्थान को संसाधित करने की सहमति के बिना, मैं सलाह प्रदान नहीं कर सकता।"
                )
                return self._build_response(request, text)
            else:
                # Ask for consent with disclaimer
                disclaimer = (
                    LEGAL_DISCLAIMER_HI
                    if request.language == "hi"
                    else LEGAL_DISCLAIMER
                )
                text = (
                    (
                        f"Welcome to KisanSaathi! Before we start, I need your consent to temporarily "
                        f"process your voice notes and store your location for agricultural advisories.\n\n"
                        f"Legal Disclaimer:\n{disclaimer}\n\n"
                        f"Do you agree? (Yes/No)"
                    )
                    if request.language != "hi"
                    else (
                        f"किसानसाथी में आपका स्वागत है! शुरू करने से पहले, मुझे आपके वॉयस नोट्स को "
                        f"संसाधित करने और कृषि सलाह के लिए आपके स्थान को संग्रहीत करने के लिए "
                        f"आपकी सहमति की आवश्यकता है।\n\n"
                        f"कानूनी अस्वीकरण:\n{disclaimer}\n\n"
                        f"क्या आप सहमत हैं? (हाँ/नहीं)"
                    )
                )
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
                text = (
                    "Got it. What is the primary crop you are growing right now?"
                    if request.language != "hi"
                    else "समझ गया। अभी आप मुख्य रूप से कौन सी फसल उगा रहे हैं?"
                )
                return self._build_response(request, text)
            else:
                text = (
                    "Please provide both your state and district, separated by a comma. (e.g., 'Maharashtra, Pune')"
                    if request.language != "hi"
                    else "कृपया अपना राज्य और जिला दोनों प्रदान करें, अल्पविराम द्वारा अलग किए गए। (उदा., 'महाराष्ट्र, पुणे')"
                )
                return self._build_response(request, text)

        elif step == "crop":
            profile.crop = request.query_text.strip()
            profile.onboarding_step = "details"
            await db.commit()
            text = (
                "Almost done! How many hectares of land do you farm, and are you a small, marginal, or large farmer? (e.g., '2 hectares, small')"
                if request.language != "hi"
                else "लगभग पूरा हो गया! आप कितने हेक्टेयर भूमि पर खेती करते हैं, और क्या आप एक छोटे, सीमांत या बड़े किसान हैं? (उदा., '2 हेक्टेयर, छोटे')"
            )
            return self._build_response(request, text)

        elif step == "details":
            parts = request.query_text.split(",")
            if len(parts) >= 2:
                # Extract numbers from parts[0]
                match = re.search(r"\d+(?:\.\d+)?", parts[0])
                if match:
                    profile.land_size_ha = match.group(0)
                profile.category = parts[1].strip()
                profile.onboarding_step = "language"
                await db.commit()
                text = (
                    "What is your preferred language for responses? (en/hi/mr)"
                    if request.language != "hi"
                    else "आपकी प्रतिक्रियाओं के लिए पसंदीदा भाषा क्या है? (en/hi/mr)"
                )
                return self._build_response(request, text)
            else:
                text = (
                    "Please provide your land size and category, separated by a comma. (e.g., '2 hectares, small')"
                    if request.language != "hi"
                    else "कृपया अपनी भूमि का आकार और श्रेणी प्रदान करें, अल्पविराम द्वारा अलग किए गए। (उदा., '2 हेक्टेयर, छोटे')"
                )
                return self._build_response(request, text)

        elif step == "language":
            lang = request.query_text.strip().lower()
            valid_langs = ["en", "hi", "mr"]
            if lang not in valid_langs:
                text = (
                    "Please choose a valid language: en (English), hi (Hindi), or mr (Marathi)."
                    if request.language != "hi"
                    else "कृपया वैध भाषा चुनें: en (अंग्रेज़ी), hi (हिंदी), या mr (मराठी)।"
                )
                return self._build_response(request, text)

            profile.language = lang
            profile.onboarding_step = "pump"
            await db.commit()
            text = (
                (
                    "Optional: Do you use a diesel or electric pump for irrigation? "
                    "If yes, what is the motor horsepower (HP)? "
                    "Reply like 'diesel, 5' or 'electric, 3' or say 'skip' to finish."
                )
                if lang != "hi"
                else (
                    "वैकल्पिक: क्या आप सिंचाई के लिए डीजल या इलेक्ट्रिक पंप का उपयोग करते हैं? "
                    "अगर हाँ, तो मोटर की हॉर्सपावर (HP) क्या है? "
                    "'डीजल, 5' या 'इलेक्ट्रिक, 3' जैसे जवाब दें या 'स्किप' कहकर पूरा करें।"
                )
            )
            return self._build_response(request, text)

        elif step == "pump":
            text_lower = request.query_text.lower().strip()
            if "skip" in text_lower or "नहीं" in text_lower or "nahi" in text_lower:
                profile.onboarding_step = "complete"
                await db.commit()
                text = (
                    "Your profile is set up! You can now ask me about irrigation, spoilage risks, subsidies, or market prices."
                    if request.language != "hi"
                    else "आपकी प्रोफ़ाइल सेट हो गई है! अब आप मुझसे सिंचाई, खराब होने के जोखिमों, सब्सिडी या बाजार की कीमतों के बारे में पूछ सकते हैं।"
                )
                return self._build_response(request, text)

            # Parse pump type and motor HP
            parts = request.query_text.split(",")
            if len(parts) >= 2:
                pump_type = parts[0].strip().lower()
                hp_text = parts[1].strip()

                # Validate pump type
                if pump_type not in ["diesel", "electric", "डीजल", "इलेक्ट्रिक"]:
                    text = (
                        "Please specify 'diesel' or 'electric' for pump type, and the motor HP. (e.g., 'diesel, 5')"
                        if request.language != "hi"
                        else "कृपया पंप प्रकार के लिए 'डीजल' या 'इलेक्ट्रिक' और मोटर HP बताएं। (उदा., 'डीजल, 5')"
                    )
                    return self._build_response(request, text)

                # Normalize pump type
                if pump_type in ["डीजल"]:
                    pump_type = "diesel"
                elif pump_type in ["इलेक्ट्रिक"]:
                    pump_type = "electric"

                # Extract HP
                hp_match = re.search(r"\d+(?:\.\d+)?", hp_text)
                if not hp_match:
                    text = (
                        "Please provide motor horsepower as a number. (e.g., 'diesel, 5')"
                        if request.language != "hi"
                        else "कृपया मोटर हॉर्सपावर को संख्या में बताएं। (उदा., 'डीजल, 5')"
                    )
                    return self._build_response(request, text)

                motor_hp = float(hp_match.group(0))

                profile.pump_type = pump_type
                profile.motor_hp = motor_hp  # type: ignore
                profile.onboarding_step = "complete"
                await db.commit()

                text = (
                    f"Got it! {pump_type.capitalize()} pump with {motor_hp} HP motor. Your profile is set up! You can now ask me about irrigation, spoilage risks, subsidies, or market prices."
                    if request.language != "hi"
                    else f"समझ गया! {motor_hp} HP का {pump_type} पंप। आपकी प्रोफ़ाइल सेट हो गई है! अब आप मुझसे सिंचाई, खराब होने के जोखिमों, सब्सिडी या बाजार की कीमतों के बारे में पूछ सकते हैं।"
                )
                return self._build_response(request, text)
            else:
                text = (
                    "Please provide pump type and motor HP separated by a comma. (e.g., 'diesel, 5') or say 'skip'."
                    if request.language != "hi"
                    else "कृपया पंप प्रकार और मोटर HP अल्पविराम से अलग करके बताएं। (उदा., 'डीजल, 5') या 'स्किप' कहें।"
                )
                return self._build_response(request, text)

        return self._build_response(request, "Onboarding complete.", safe_fallback=True)

    async def handle_deletion_request(
        self, request: AgentRequest, db: AsyncSession
    ) -> AgentResponse:
        """
        Handle 'delete my data' requests.
        For MVP: Queue for human review and confirm via WhatsApp.
        """
        farmer_id = request.farmer_id
        language = request.language

        # Get profile
        result = await db.execute(
            select(FarmerProfileDB).filter(FarmerProfileDB.phone_number == farmer_id)
        )
        profile = result.scalars().first()

        if not profile:
            text = (
                "No profile found for your number."
                if language != "hi"
                else "आपके नंबर के लिए कोई प्रोफ़ाइल नहीं मिली।"
            )
            return self._build_response(request, text)

        # Check if already queued for deletion
        if profile.onboarding_step == "deletion_queued":
            text = (
                (
                    "Your data deletion request is already queued for review. "
                    "Our team will process it within 7 business days."
                )
                if language != "hi"
                else (
                    "आपका डेटा डिलीशन अनुरोध पहले से ही समीक्षा के लिए कतार में है। "
                    "हमारी टीम इसे 7 कार्य दिवसों के भीतर संसाधित करेगी।"
                )
            )
            return self._build_response(request, text)

        # Queue for deletion (mark for human review)
        profile.onboarding_step = "deletion_queued"
        await db.commit()

        # In production, also create a DeletionRequest record for audit trail
        # await db.execute(insert(DeletionRequest).values(...))

        logger.info(f"Deletion request queued for farmer {farmer_id}")

        if language != "hi":
            text = (
                "We've received your request to delete your data. "
                "This request has been queued for human review. "
                "Our team will verify your identity and process the deletion within 7 business days. "
                "You'll receive a confirmation via WhatsApp once complete."
            )
        else:
            text = (
                "हमें आपके डेटा को हटाने का अनुरोध प्राप्त हुआ है। "
                "यह अनुरोध मानवीय समीक्षा के लिए कतार में है। "
                "हमारी टीम आपकी पहचान सत्यापित करेगी और 7 कार्य दिवसों के भीतर डिलीशन संसाधित करेगी। "
                "पूरा होने पर आपको व्हाट्सएप पर पुष्टि मिल जाएगी।"
            )

        return self._build_response(request, text, safe_fallback=True)

    def _build_response(
        self, request: AgentRequest, text: str, **kwargs
    ) -> AgentResponse:
        return AgentResponse(
            text=text,
            agent_name="OnboardingAgent",
            intent="onboarding",
            response_timestamp=datetime.utcnow(),
            **kwargs,
        )

import logging
import re
from datetime import datetime

from ..models.contracts import AgentRequest, AgentResponse
from ..integrations.market import MarketClient

logger = logging.getLogger(__name__)

class MarketPriceAgent:
    def __init__(self, market_client: MarketClient):
        self.market_client = market_client

    async def process_request(self, request: AgentRequest) -> AgentResponse:
        state = request.profile.get("state")
        district = request.profile.get("district")
        crop = request.profile.get("crop", "").lower()

        # Validate Profile
        if not crop:
            text = "Which crop's price do you want to check?" if request.language != "hi" else "आप किस फसल की कीमत जांचना चाहते हैं?"
            return self._build_response(request, text, safe_fallback=True)

        if not state or not district:
            text = "I need your state and district to find the local Mandi price. Please update your profile or tell me where you are." if request.language != "hi" else "मुझे स्थानीय मंडी की कीमत खोजने के लिए आपके राज्य और जिले की आवश्यकता है। कृपया अपनी प्रोफ़ाइल अपडेट करें।"
            return self._build_response(request, text, safe_fallback=True)

        # Extract offered price from the query using basic regex
        # Look for words like "offering 2000", "2000 per quintal", "price 2000"
        offered_price = None
        match = re.search(r'(?:rs|rs\.|rupees|₹)?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:rs|rs\.|rupees|₹|per|/|-|for)?', request.query_text.lower())
        if match:
             try:
                 # Remove commas and convert to float
                 num_str = match.group(1).replace(",", "")
                 offered_price = float(num_str)
             except ValueError:
                 pass

        # Fetch Verified Price
        market_data = await self.market_client.get_mandi_price(crop, state, district)
        if not market_data:
             text = f"I couldn't find verified price data for {crop} in your region right now." if request.language != "hi" else f"मुझे अभी आपके क्षेत्र में {crop} के लिए सत्यापित मूल्य डेटा नहीं मिल सका।"
             return self._build_response(request, text, safe_fallback=True, verification_status="failed")

        mandi_price = market_data.mandi_price_inr_per_qtl
        msp = market_data.msp_inr_per_qtl

        # Recommendation Logic
        if offered_price:
             if offered_price < mandi_price:
                 text_en = f"Warning: The offered price of ₹{offered_price} is LOWER than the local Mandi price (₹{mandi_price}/quintal). Do not sell. Negotiate or sell at the Mandi."
                 text_hi = f"चेतावनी: ₹{offered_price} की पेशकश की गई कीमत स्थानीय मंडी की कीमत (₹{mandi_price}/क्विंटल) से कम है। न बेचें। बातचीत करें या मंडी में बेचें।"
             else:
                 text_en = f"Good news: The offered price of ₹{offered_price} is fair. The local Mandi price is ₹{mandi_price}/quintal."
                 text_hi = f"खुशखबरी: ₹{offered_price} की पेशकश की गई कीमत उचित है। स्थानीय मंडी की कीमत ₹{mandi_price}/क्विंटल है।"
                 
             if msp and offered_price < msp:
                 text_en += f" Note: The Govt MSP is ₹{msp}/quintal."
                 text_hi += f" ध्यान दें: सरकारी MSP ₹{msp}/क्विंटल है।"
                 
        else:
             text_en = f"The current verified Mandi price for {crop} in {district} is ₹{mandi_price}/quintal."
             text_hi = f"{district} में {crop} के लिए वर्तमान सत्यापित मंडी मूल्य ₹{mandi_price}/क्विंटल है।"
             if msp:
                 text_en += f" The Govt Minimum Support Price (MSP) is ₹{msp}/quintal."
                 text_hi += f" सरकारी न्यूनतम समर्थन मूल्य (MSP) ₹{msp}/क्विंटल है।"

        text = text_hi if request.language == "hi" else text_en

        return self._build_response(
            request=request,
            text=text,
            source_name=market_data.source,
            source_timestamp=market_data.retrieved_at,
            verification_status="verified",
        )

    def _build_response(self, request: AgentRequest, text: str, **kwargs) -> AgentResponse:
        return AgentResponse(
            text=text,
            agent_name="MarketPriceAgent",
            intent="market_price",
            response_timestamp=datetime.utcnow(),
            **kwargs
        )

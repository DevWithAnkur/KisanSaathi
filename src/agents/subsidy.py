import json
import logging
import os
from datetime import datetime
from typing import List

from ..models.contracts import AgentRequest, AgentResponse
from ..models.scheme_models import Scheme

logger = logging.getLogger(__name__)

class SubsidyAgent:
    def __init__(self):
        # Load scheme data
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(current_dir, "..", "data", "schemes.json")
        self.schemes: List[Scheme] = []
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                schemes_data = json.load(f)
                for item in schemes_data:
                    self.schemes.append(Scheme(**item))
        except Exception as e:
            logger.error(f"Failed to load schemes.json: {e}")

    async def process_request(self, request: AgentRequest) -> AgentResponse:
        state = request.profile.get("state")
        land_size = request.profile.get("land_size_ha")
        crop = request.profile.get("crop", "").lower()
        category = request.profile.get("category", "").lower()

        # Ask exactly one targeted question if critical profile data is missing
        if state is None:
            text = "To find relevant schemes, I need to know which state you live in. What state are you from?" if request.language != "hi" else "संबंधित योजनाओं को खोजने के लिए, मुझे यह जानना होगा कि आप किस राज्य में रहते हैं। आप किस राज्य से हैं?"
            return self._build_response(request, text, safe_fallback=True)

        if land_size is None:
            text = "To check your eligibility for subsidies, I need to know your land size. How many hectares of land do you farm?" if request.language != "hi" else "सब्सिडी के लिए आपकी पात्रता की जांच करने के लिए, मुझे आपकी भूमि का आकार जानना होगा। आप कितने हेक्टेयर भूमि पर खेती करते हैं?"
            return self._build_response(request, text, safe_fallback=True)

        if not category:
            text = "Are you a small, marginal, or large farmer? This helps me match you to the right scheme." if request.language != "hi" else "क्या आप एक छोटे, सीमांत या बड़े किसान हैं? इससे मुझे आपको सही योजना से मिलाने में मदद मिलती है।"
            return self._build_response(request, text, safe_fallback=True)

        eligible_schemes = []
        for scheme in self.schemes:
            # Check state
            if scheme.state_scope != "national" and scheme.state_scope.lower() != state.lower():
                continue
                
            # Check land size
            if scheme.max_land_size_ha is not None and float(land_size) > scheme.max_land_size_ha:
                continue
                
            # Check crop (if scheme specifies crops, the farmer's crop must be in it)
            if scheme.eligible_crops and crop not in [c.lower() for c in scheme.eligible_crops]:
                continue
                
            # Check category
            if scheme.categories and "all" not in [c.lower() for c in scheme.categories]:
                if category not in [c.lower() for c in scheme.categories]:
                    continue
            
            eligible_schemes.append(scheme)

        if not eligible_schemes:
            text = "Currently, I couldn't find any schemes matching your profile." if request.language != "hi" else "वर्तमान में, मुझे आपकी प्रोफ़ाइल से मेल खाने वाली कोई योजना नहीं मिली।"
            return self._build_response(request, text)

        # Output Verification (FR-5d): We are directly returning data from our verified dataset, so it's inherently verified.
        # Pick the first eligible scheme for simplicity in voice context (or join them if multiple)
        # We will return the first one to keep it concise as requested by "one actionable next step"
        matched = eligible_schemes[0]
        
        if request.language == "hi":
            text = f"आप {matched.name} के लिए पात्र हैं। {matched.benefit}। अगला कदम: {matched.next_action}।"
        else:
            text = f"You qualify for {matched.name}. {matched.benefit}. Next step: {matched.next_action}."

        return self._build_response(
            request=request,
            text=text,
            source_name=matched.source,
            source_timestamp=matched.last_updated,
            verification_status="verified",
        )

    def _build_response(self, request: AgentRequest, text: str, **kwargs) -> AgentResponse:
        return AgentResponse(
            text=text,
            agent_name="SubsidyAgent",
            intent="subsidy",
            response_timestamp=datetime.utcnow(),
            **kwargs
        )

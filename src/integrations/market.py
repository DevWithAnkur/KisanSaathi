import logging
from datetime import datetime
from typing import Optional

from ..models.market_models import MarketPrice

logger = logging.getLogger(__name__)

class MarketClient:
    def __init__(self):
        # Mock database for MVP
        self.mock_db = {
            "wheat": {"mandi_price": 2350.0, "msp": 2275.0},
            "rice": {"mandi_price": 2100.0, "msp": 2183.0},
            "cotton": {"mandi_price": 6500.0, "msp": 6620.0},
            "tomato": {"mandi_price": 1800.0, "msp": None}, # Veggies often don't have MSP
            "potato": {"mandi_price": 1200.0, "msp": None},
        }

    async def get_mandi_price(self, crop: str, state: str, district: str) -> Optional[MarketPrice]:
        """
        Fetches the latest mandi price and MSP for a given crop and location.
        In production, this would call the Agmarknet/eNAM API.
        """
        crop_key = crop.lower()
        if crop_key not in self.mock_db:
            logger.warning(f"No mock market data for crop: {crop}")
            return None
            
        data = self.mock_db[crop_key]
        
        # Add some slight variation based on district hash to make it look "live"
        variation = (hash(district) % 100) - 50 
        final_mandi_price = data["mandi_price"] + variation
        
        return MarketPrice(
            crop=crop_key,
            state=state,
            district=district,
            mandi_price_inr_per_qtl=final_mandi_price,
            msp_inr_per_qtl=data["msp"],
            source="Agmarknet (Mock)",
            retrieved_at=datetime.utcnow()
        )

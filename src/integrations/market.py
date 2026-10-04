import logging
import httpx
from datetime import datetime
from typing import Optional, Dict, List
import os

from ..models.market_models import MarketPrice

logger = logging.getLogger(__name__)


class AgmarknetClient:
    """
    Client for Agmarknet (Government of India Agricultural Marketing Information Network) API.
    API documentation: https://agmarknet.gov.in/
    """
    
    BASE_URL = "https://api.agmarknet.gov.in"  # Placeholder - actual endpoint may differ
    
    # Crop code mapping (Agmarknet uses specific crop codes)
    CROP_CODES = {
        "wheat": "0101",
        "rice": "0102",
        "maize": "0103",
        "cotton": "0201",
        "soybean": "0202",
        "groundnut": "0203",
        "mustard": "0204",
        "tomato": "0301",
        "potato": "0302",
        "onion": "0303",
    }
    
    def __init__(self, api_key: str = None, timeout: int = 30):
        self.api_key = api_key or os.getenv("AGMARKNET_API_KEY")
        self.timeout = timeout
        self._client = None
        
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
        return self._client
    
    async def get_mandi_prices(self, crop: str, state: str, district: str) -> Optional[List[Dict]]:
        """
        Fetch mandi prices for a crop in a specific state/district.
        Returns list of mandi price records.
        """
        if not self.api_key:
            logger.warning("Agmarknet API key not configured, using mock data")
            return None
            
        crop_code = self.CROP_CODES.get(crop.lower())
        if not crop_code:
            logger.warning(f"No Agmarknet crop code for: {crop}")
            return None
            
        try:
            client = await self._get_client()
            
            # Agmarknet API endpoint (example - actual may differ)
            params = {
                "crop_code": crop_code,
                "state": state,
                "district": district,
                "date": datetime.now().strftime("%Y-%m-%d")
            }
            
            response = await client.get(
                f"{self.BASE_URL}/api/mandi-prices",
                params=params
            )
            
            if response.status_code == 404:
                logger.info(f"No price data found for {crop} in {district}, {state}")
                return None
                
            response.raise_for_status()
            data = response.json()
            
            # Parse response - structure depends on actual API
            return self._parse_response(data, crop, state, district)
            
        except httpx.TimeoutException:
            logger.error(f"Agmarknet API timeout for {crop} in {district}, {state}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Agmarknet API error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Agmarknet API unexpected error: {e}")
            return None
    
    def _parse_response(self, data: Dict, crop: str, state: str, district: str) -> List[Dict]:
        """Parse Agmarknet API response into standardized format."""
        results = []
        
        # Handle different possible response structures
        records = data.get("data") or data.get("records") or data.get("prices") or []
        
        for record in records:
            try:
                # Extract price info (field names may vary)
                mandi_name = record.get("mandi_name") or record.get("market") or "Unknown"
                modal_price = record.get("modal_price") or record.get("price") or 0
                min_price = record.get("min_price") or record.get("minimum") or modal_price
                max_price = record.get("max_price") or record.get("maximum") or modal_price
                
                results.append({
                    "mandi_name": mandi_name,
                    "modal_price": float(modal_price),
                    "min_price": float(min_price),
                    "max_price": float(max_price),
                    "arrival_date": record.get("arrival_date") or record.get("date"),
                    "unit": record.get("unit", "Quintal")
                })
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse price record: {e}")
                continue
                
        return results
    
    async def close(self):
        if self._client:
            await self._client.aclose()


class MarketClient:
    """
    Unified market price client with Agmarknet integration and mock fallback.
    """
    
    def __init__(self, agmarknet_api_key: str = None, use_mock: bool = False):
        self.use_mock = use_mock or not agmarknet_api_key
        self.agmarknet = AgmarknetClient(api_key=agmarknet_api_key) if not self.use_mock else None
        
        # Mock database for MVP / fallback
        self.mock_db = {
            "wheat": {"mandi_price": 2350.0, "msp": 2275.0},
            "rice": {"mandi_price": 2100.0, "msp": 2183.0},
            "maize": {"mandi_price": 1950.0, "msp": 2090.0},
            "cotton": {"mandi_price": 6500.0, "msp": 6620.0},
            "soybean": {"mandi_price": 4600.0, "msp": 4600.0},
            "groundnut": {"mandi_price": 5800.0, "msp": 5850.0},
            "mustard": {"mandi_price": 5650.0, "msp": 5650.0},
            "tomato": {"mandi_price": 1800.0, "msp": None},
            "potato": {"mandi_price": 1200.0, "msp": None},
            "onion": {"mandi_price": 1500.0, "msp": None},
        }
        
        # MSP data (static for now, could be fetched from separate source)
        self.msp_data = {
            "wheat": 2275.0,
            "rice": 2183.0,
            "maize": 2090.0,
            "cotton": 6620.0,
            "soybean": 4600.0,
            "groundnut": 5850.0,
            "mustard": 5650.0,
        }

    async def get_mandi_price(self, crop: str, state: str, district: str) -> Optional[MarketPrice]:
        """
        Fetches the latest mandi price and MSP for a given crop and location.
        Tries Agmarknet API first, falls back to mock data.
        """
        crop_key = crop.lower()
        
        # Try Agmarknet API if not in mock mode
        if not self.use_mock and self.agmarknet:
            try:
                prices = await self.agmarknet.get_mandi_prices(crop, state, district)
                if prices:
                    return self._build_from_agmarknet(prices, crop, state, district)
            except Exception as e:
                logger.warning(f"Agmarknet fetch failed, falling back to mock: {e}")
        
        # Fallback to mock data
        return self._get_mock_price(crop_key, state, district)

    def _build_from_agmarknet(self, prices: List[Dict], crop: str, state: str, district: str) -> MarketPrice:
        """Build MarketPrice from Agmarknet API response."""
        if not prices:
            return None
            
        # Use modal price from first mandi (or average across mandis)
        modal_prices = [p["modal_price"] for p in prices if p.get("modal_price")]
        if not modal_prices:
            return None
            
        avg_modal_price = sum(modal_prices) / len(modal_prices)
        min_price = min(p["min_price"] for p in prices if p.get("min_price"))
        max_price = max(p["max_price"] for p in prices if p.get("max_price"))
        
        mandi_names = [p["mandi_name"] for p in prices if p.get("mandi_name")]
        source = f"Agmarknet ({', '.join(mandi_names[:3])})"
        
        return MarketPrice(
            crop=crop.lower(),
            state=state,
            district=district,
            mandi_price_inr_per_qtl=avg_modal_price,
            msp_inr_per_qtl=self.msp_data.get(crop.lower()),
            source=source,
            retrieved_at=datetime.utcnow()
        )

    def _get_mock_price(self, crop_key: str, state: str, district: str) -> Optional[MarketPrice]:
        """Get mock price data for development/testing."""
        if crop_key not in self.mock_db:
            logger.warning(f"No mock market data for crop: {crop_key}")
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

    async def close(self):
        if self.agmarknet:
            await self.agmarknet.close()


# Global instance (configured via settings in production)
market_client = MarketClient()
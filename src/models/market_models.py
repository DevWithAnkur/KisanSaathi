from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MarketPrice(BaseModel):
    crop: str
    state: str
    district: str
    mandi_price_inr_per_qtl: float
    msp_inr_per_qtl: Optional[float]
    source: str
    retrieved_at: datetime

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Scheme(BaseModel):
    name: str = Field(..., description="Name of the scheme")
    state_scope: str = Field(..., description="State or 'national'")
    eligible_crops: List[str] = Field(default_factory=list, description="Crops eligible for this scheme, empty means all")
    max_land_size_ha: Optional[float] = Field(None, description="Maximum land size in hectares, None if no limit")
    categories: List[str] = Field(default_factory=list, description="Categories eligible, e.g., 'small', 'marginal', 'all'")
    benefit: str = Field(..., description="One-line description of the benefit")
    next_action: str = Field(..., description="The next action the farmer should take")
    source: str = Field(..., description="Official source URL or portal name")
    last_updated: datetime = Field(..., description="When the scheme data was last updated")
    dataset_version: str = Field("1.0", description="Version of the dataset")

from pydantic import BaseModel, Field
from typing import List, Optional
class Claim(BaseModel):
    claim: str = Field(..., description="The statement extracted from the text.")
    section: str = Field("Unknown", description="The document section where the claim was found.")
class Contradiction(BaseModel):
    description: str = Field(..., description="Description of the contradiction found between claims.")
class FactCheckResult(BaseModel):
    claim: str
    is_outdated: Optional[bool] = Field(None, description="True if obsolete, False if current, None if unverifiable.")
    latest_info: str = Field(..., description="Supporting context or corrected information.")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
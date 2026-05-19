from typing import Dict, Optional

from pydantic import BaseModel, Field

from ..base_client import BaseRequestModel


class PetInfo(BaseModel):
    name: str = Field(default="", description="Pet's name")
    breed: str = Field(default="", description="Breed, e.g. 'Poodle', 'Husky'")
    weight: str = Field(default="", description="Weight with unit, e.g. '12 kg'")
    age: str = Field(default="", description="Age, e.g. '3 years', '6 months'")
    coat: str = Field(default="", description="Coat condition, e.g. 'matted', 'smooth'")


class QualifyLeadRequest(BaseRequestModel):
    name: str = Field(default="", description="Customer's name")
    phone: str = Field(default="", description="Customer phone (digits + optional '+')")
    note: str = Field(default="", description="Optional customer note")
    pet: PetInfo = Field(default_factory=PetInfo)


class QualifyLeadResponse(BaseModel):
    qualified: bool
    lead_id: str
    pet_id: Optional[str] = None
    error: Optional[str] = None


class GetQualificationStatusRequest(BaseRequestModel):
    """Empty request — internal metadata (_lead_id) supplies the lookup key."""


class GetQualificationStatusResponse(BaseModel):
    lead_id: str
    status: str
    name: str = ""
    phone: str = ""
    pet: Dict[str, str] = Field(default_factory=dict)

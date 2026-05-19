from typing import List, Optional

from pydantic import BaseModel, Field

from ..base_client import BaseRequestModel
from ..qualification_mcp.models import PetInfo


class ServiceLine(BaseModel):
    service_id: str
    title: str
    description: str = ""
    base_price: float
    final_price: float
    duration_min: int
    is_fallback: bool = False
    fallback_reason: Optional[str] = None


class ListServicesRequest(BaseRequestModel):
    pet: PetInfo = Field(
        default_factory=PetInfo,
        description="Pet info used to price each service (weight bracket + breed modifier).",
    )


class ListServicesResponse(BaseModel):
    services: List[ServiceLine]
    recommended_service_id: Optional[str] = None
    formatted_text: str = ""


class SelectServiceRequest(BaseRequestModel):
    user_text: str = Field(
        description="Free-text user reply naming a service (title, id, or fuzzy phrase). "
                    "Also accepts 'yes/ok/sure' to accept the recommendation."
    )
    pet: PetInfo = Field(default_factory=PetInfo)
    recommended_service_id: str = Field(
        default="",
        description="The currently-recommended service id (used to resolve affirmative replies).",
    )


class SelectServiceResponse(BaseModel):
    selected: Optional[ServiceLine] = None
    matched: bool
    reply_hint: str = ""

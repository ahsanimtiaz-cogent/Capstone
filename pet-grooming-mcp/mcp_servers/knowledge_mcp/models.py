from typing import Dict, List

from pydantic import BaseModel

from ..base_client import BaseRequestModel


class GetBrandConfigRequest(BaseRequestModel):
    """Empty payload — returns the BrandConfig row."""


class GetBrandConfigResponse(BaseModel):
    brand_id: str
    brand_name: str
    welcome_copy: str
    hours: str
    location: str
    timezone: str
    upsells: List[Dict[str, object]] = []
    objection_snippets: Dict[str, str] = {}

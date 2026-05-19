"""Knowledge business logic: surface BrandConfig from Sheets."""
from ..base_client import BaseMCPClient
from ..mcp_utils import get_sheets
from .models import GetBrandConfigRequest, GetBrandConfigResponse


class KnowledgeMCPClient(BaseMCPClient):

    def get_brand_config(
        self, _request: GetBrandConfigRequest
    ) -> GetBrandConfigResponse:
        brand = get_sheets().get_brand_config()
        return GetBrandConfigResponse(
            brand_id=str(brand.get("brand_id", "")),
            brand_name=brand.get("brand_name", ""),
            welcome_copy=brand.get("welcome_copy", ""),
            hours=brand.get("hours", ""),
            location=brand.get("location", ""),
            timezone=brand.get("timezone", "UTC"),
            upsells=brand.get("upsells_json", []) or [],
            objection_snippets=brand.get("objection_snippets_json", {}) or {},
        )

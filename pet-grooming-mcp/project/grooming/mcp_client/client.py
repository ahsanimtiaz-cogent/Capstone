"""Thin facade over the five MCP domain clients.

Methods accept a `ctx` dict ({"_lead_id", "_discord_user_id", ...}) plus
typed kwargs; they construct the request model, instantiate the right
domain client, and invoke the tool body directly. Returns the typed response.

The domain client methods are sync — gspread/Google Calendar/Django ORM
are all sync APIs. The MCP server (`mcp_servers/grooming_mcp_server.py`)
still exposes them as `async def` tools at the FastMCP layer; this facade
skips that layer for the in-process call path.
"""
from typing import Any, Dict, Optional

from mcp_servers.booking_mcp.client import BookingMCPClient
from mcp_servers.booking_mcp.models import (
    BookAppointmentRequest,
    BookAppointmentResponse,
    FetchFreeSlotsRequest,
    FetchFreeSlotsResponse,
    ShowHoursRequest,
    ShowHoursResponse,
)
from mcp_servers.followup_mcp.client import FollowupMCPClient
from mcp_servers.followup_mcp.models import (
    CancelFollowupRequest,
    CancelFollowupResponse,
    ListFollowupsRequest,
    ListFollowupsResponse,
    ScheduleFollowupRequest,
    ScheduleFollowupResponse,
)
from mcp_servers.knowledge_mcp.client import KnowledgeMCPClient
from mcp_servers.knowledge_mcp.models import (
    GetBrandConfigRequest,
    GetBrandConfigResponse,
)
from mcp_servers.qualification_mcp.client import QualificationMCPClient
from mcp_servers.qualification_mcp.models import (
    GetQualificationStatusRequest,
    GetQualificationStatusResponse,
    PetInfo,
    QualifyLeadRequest,
    QualifyLeadResponse,
)
from mcp_servers.services_mcp.client import ServicesMCPClient
from mcp_servers.services_mcp.models import (
    ListServicesRequest,
    ListServicesResponse,
    SelectServiceRequest,
    SelectServiceResponse,
)


def _merge_meta(payload: Dict[str, Any], ctx: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    out = dict(payload)
    if ctx:
        for k, v in ctx.items():
            if k.startswith("_"):
                out[k] = v
    return out


class MCPClient:
    """Sync facade over the in-process MCP domain clients."""

    # ---- qualification ----------------------------------------------------

    def qualify_lead(self, ctx: Dict[str, Any], **payload) -> QualifyLeadResponse:
        if "pet" in payload and isinstance(payload["pet"], dict):
            payload["pet"] = PetInfo(**payload["pet"])
        req = QualifyLeadRequest(**_merge_meta(payload, ctx))
        return QualificationMCPClient(req).qualify_lead(req)

    def get_qualification_status(self, ctx: Dict[str, Any]) -> GetQualificationStatusResponse:
        req = GetQualificationStatusRequest(**_merge_meta({}, ctx))
        return QualificationMCPClient(req).get_qualification_status(req)

    # ---- services ---------------------------------------------------------

    def list_services(self, ctx: Dict[str, Any], pet: Dict[str, Any]) -> ListServicesResponse:
        req = ListServicesRequest(**_merge_meta({"pet": PetInfo(**pet)}, ctx))
        return ServicesMCPClient(req).list_services(req)

    def select_service(self, ctx: Dict[str, Any], user_text: str, pet: Dict[str, Any],
                       recommended_service_id: str = "") -> SelectServiceResponse:
        req = SelectServiceRequest(**_merge_meta({
            "user_text": user_text,
            "pet": PetInfo(**pet),
            "recommended_service_id": recommended_service_id,
        }, ctx))
        return ServicesMCPClient(req).select_service(req)

    # ---- booking ----------------------------------------------------------

    def show_hours(self, ctx: Dict[str, Any]) -> ShowHoursResponse:
        req = ShowHoursRequest(**_merge_meta({}, ctx))
        return BookingMCPClient(req).show_hours(req)

    def fetch_free_slots(self, ctx: Dict[str, Any], day: str, service_id: str
                         ) -> FetchFreeSlotsResponse:
        req = FetchFreeSlotsRequest(**_merge_meta({"day": day, "service_id": service_id}, ctx))
        return BookingMCPClient(req).fetch_free_slots(req)

    def book_appointment(self, ctx: Dict[str, Any], day: str, start_time: str,
                         service_id: str, pet_name: str = "your pet"
                         ) -> BookAppointmentResponse:
        req = BookAppointmentRequest(**_merge_meta({
            "day": day, "start_time": start_time,
            "service_id": service_id, "pet_name": pet_name,
        }, ctx))
        return BookingMCPClient(req).book_appointment(req)

    # ---- followup --------------------------------------------------------

    def schedule_followup(self, ctx: Dict[str, Any], message: str = "",
                          delay_hours: float = 24.0) -> ScheduleFollowupResponse:
        payload: Dict[str, Any] = {"delay_hours": delay_hours}
        if message:
            payload["message"] = message
        req = ScheduleFollowupRequest(**_merge_meta(payload, ctx))
        return FollowupMCPClient(req).schedule_followup(req)

    def list_followups(self, ctx: Dict[str, Any]) -> ListFollowupsResponse:
        req = ListFollowupsRequest(**_merge_meta({}, ctx))
        return FollowupMCPClient(req).list_followups(req)

    def cancel_followup(self, ctx: Dict[str, Any], job_id: str) -> CancelFollowupResponse:
        req = CancelFollowupRequest(**_merge_meta({"job_id": job_id}, ctx))
        return FollowupMCPClient(req).cancel_followup(req)

    # ---- knowledge -------------------------------------------------------

    def get_brand_config(self, ctx: Dict[str, Any]) -> GetBrandConfigResponse:
        req = GetBrandConfigRequest(**_merge_meta({}, ctx))
        return KnowledgeMCPClient(req).get_brand_config(req)

"""Services business logic: list/recommend, fuzzy-match user reply to a service."""
from ..base_client import BaseMCPClient
from ..mcp_utils import get_sheets
from project.grooming.integrations.matching_service import (
    find_best_service,
    format_services_list,
    match_service_by_user_input,
    price_for_service,
)
from .models import (
    ListServicesRequest,
    ListServicesResponse,
    SelectServiceRequest,
    SelectServiceResponse,
    ServiceLine,
)


_AFFIRMATIVES = {"yes", "y", "yeah", "sure", "ok", "okay", "please", "go ahead"}


def _line_from_service(svc: dict, pet: dict) -> ServiceLine:
    final, is_fallback, reason = price_for_service(svc, pet)
    return ServiceLine(
        service_id=svc["service_id"],
        title=svc["title"],
        description=svc.get("description", ""),
        base_price=svc["base_price"],
        final_price=final,
        duration_min=svc["duration_min"],
        is_fallback=is_fallback,
        fallback_reason=reason,
    )


class ServicesMCPClient(BaseMCPClient):

    def list_services(self, request: ListServicesRequest) -> ListServicesResponse:
        sheets = get_sheets()
        raw_services = sheets.list_services()
        pet = request.pet.model_dump()
        lines = [_line_from_service(s, pet) for s in raw_services]

        recommended = find_best_service(pet, raw_services) if pet.get("breed") else None
        rec_id = recommended["service_id"] if recommended else None

        formatted = format_services_list(raw_services, pet, recommended_id=rec_id)
        return ListServicesResponse(
            services=lines,
            recommended_service_id=rec_id,
            formatted_text=formatted,
        )

    def select_service(self, request: SelectServiceRequest) -> SelectServiceResponse:
        sheets = get_sheets()
        services = sheets.list_services()
        if not services:
            return SelectServiceResponse(
                matched=False,
                reply_hint="Our service menu is unavailable — please try again in a moment.",
            )

        pet = request.pet.model_dump()
        chosen = match_service_by_user_input(request.user_text, services)

        if chosen is None and request.user_text.strip().lower() in _AFFIRMATIVES:
            rec_id = request.recommended_service_id
            if rec_id:
                chosen = sheets.get_service(rec_id)

        if chosen is None:
            return SelectServiceResponse(
                matched=False,
                reply_hint="Could not match user input to any service.",
            )

        return SelectServiceResponse(
            matched=True,
            selected=_line_from_service(chosen, pet),
        )

"""Booking + service-inquiry dispatch — direct port of lang-graph/graph/routers/booking_router.py."""
from typing import Any, Dict

from .stages import Stages


def booking_dispatch(session: Dict[str, Any]) -> str:
    """Pick the right entry node for a BOOKING-intent message based on stage."""
    stage = session.get("stage", Stages.INITIATED)

    if stage == Stages.BOOKED:
        return "end"
    if stage in (Stages.INITIATED, Stages.QUALIFYING):
        return "extract"
    if stage == Stages.QUALIFIED:
        return "show_services"
    if stage == Stages.SERVICE_SELECTION:
        return "select_service"
    if stage == Stages.BOOKING_DAY:
        return "fetch_slots"
    if stage == Stages.BOOKING_SLOT:
        return "book"
    return "show_hours"


def service_inquiry_dispatch(session: Dict[str, Any]) -> str:
    """For SERVICE_INQUIRY intent: pick selection vs. browse."""
    stage = session.get("stage", Stages.INITIATED)
    if stage == Stages.SERVICE_SELECTION:
        return "select_service"
    return "show_services"

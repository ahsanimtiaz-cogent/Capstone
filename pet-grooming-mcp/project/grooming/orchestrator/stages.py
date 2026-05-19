"""Enums + session schema. Ported from lang-graph/graph/state.py."""
from typing import Any, Dict


class Stages:
    INITIATED = "initiated"
    QUALIFYING = "qualifying"
    QUALIFIED = "qualified"
    SERVICE_SELECTION = "service_selection"
    BOOKING_DAY = "booking_day"
    BOOKING_SLOT = "booking_slot"
    BOOKED = "booked"


class Intents:
    QUALIFICATION = "qualification"
    SERVICE_INQUIRY = "service_inquiry"
    BOOKING = "booking"
    FAQ = "faq"
    OBJECTION = "objection"


VALID_INTENTS = {
    Intents.QUALIFICATION,
    Intents.SERVICE_INQUIRY,
    Intents.BOOKING,
    Intents.FAQ,
    Intents.OBJECTION,
}


PET_FIELDS = ("name", "breed", "weight", "age", "coat")


def empty_session() -> Dict[str, Any]:
    return {
        "lead_id": None,
        "stage": Stages.INITIATED,
        "name": "",
        "phone": "",
        "city": "",
        "note": "",
        "pet": {f: "" for f in PET_FIELDS},
        "selected_service_id": None,
        "recommended_service_id": None,
        "booking_day": "",
        "followup_required": False,
    }
